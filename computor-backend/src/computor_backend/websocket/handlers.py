"""
WebSocket event handlers.

Handles incoming client events and dispatches appropriate actions.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from computor_backend.database import get_db_session
from computor_backend.model.auth import User
from computor_backend.websocket.auth import (
    authenticate_websocket_token,
    WebSocketAuthError,
    WS_CLOSE_TOKEN_EXPIRED,
)
from computor_backend.websocket.connection_manager import Connection, manager, ws_metrics
from computor_backend.websocket.pubsub import pubsub, typing_tracker, CHANNEL_PREFIX
from computor_backend.business_logic.messages import mark_message_as_read
from computor_backend.redis_cache import get_cache, get_redis_client
from computor_types.websocket import (
    parse_client_event,
    WSChannelSubscribe,
    WSChannelUnsubscribe,
    WSTypingStart,
    WSTypingStop,
    WSReadMark,
    WSPing,
    WSReauth,
    WSChannelSubscribed,
    WSChannelUnsubscribed,
    WSChannelError,
    WSTypingUpdate,
    WSReadUpdate,
    WSPong,
    WSReauthed,
    WSError,
)

logger = logging.getLogger(__name__)


async def handle_client_message(connection: Connection, raw_data: dict):
    """
    Handle an incoming message from a WebSocket client.

    Parses the event and dispatches to the appropriate handler.

    Args:
        connection: The WebSocket connection
        raw_data: Raw JSON data from the client
    """
    # Track received message
    ws_metrics.message_received()

    event = parse_client_event(raw_data)

    if event is None:
        await manager.send_to_connection(connection, WSError(
            code="INVALID_EVENT",
            message=f"Unknown or invalid event type: {raw_data.get('type', 'missing')}"
        ).model_dump())
        return

    try:
        if isinstance(event, WSChannelSubscribe):
            await handle_subscribe(connection, event)

        elif isinstance(event, WSChannelUnsubscribe):
            await handle_unsubscribe(connection, event)

        elif isinstance(event, WSTypingStart):
            await handle_typing_start(connection, event)

        elif isinstance(event, WSTypingStop):
            await handle_typing_stop(connection, event)

        elif isinstance(event, WSReadMark):
            await handle_read_mark(connection, event)

        elif isinstance(event, WSPing):
            await handle_ping(connection)

        elif isinstance(event, WSReauth):
            await handle_reauth(connection, event)

        else:
            await manager.send_to_connection(connection, WSError(
                code="UNHANDLED_EVENT",
                message=f"Event type not implemented: {event.type}"
            ).model_dump())

    except Exception as e:
        logger.error(f"Error handling event {event.type}: {e}")
        await manager.send_to_connection(connection, WSError(
            code="HANDLER_ERROR",
            message=str(e)
        ).model_dump())


async def handle_subscribe(connection: Connection, event: WSChannelSubscribe):
    """
    Handle channel subscription request.

    Validates permissions and subscribes to requested channels.
    """
    with get_db_session() as db:
        subscribed, failed = await manager.subscribe(
            connection, event.channels, db
        )

    # Send success response for subscribed channels
    if subscribed:
        await manager.send_to_connection(connection, WSChannelSubscribed(
            channels=subscribed
        ).model_dump())

    # Send error responses for failed channels
    for channel, reason in failed:
        await manager.send_to_connection(connection, WSChannelError(
            channel=channel,
            reason=reason
        ).model_dump())


async def handle_unsubscribe(connection: Connection, event: WSChannelUnsubscribe):
    """Handle channel unsubscription request."""
    unsubscribed = await manager.unsubscribe(connection, event.channels)

    if unsubscribed:
        await manager.send_to_connection(connection, WSChannelUnsubscribed(
            channels=unsubscribed
        ).model_dump())


async def handle_typing_start(connection: Connection, event: WSTypingStart):
    """
    Handle typing start event.

    Sets typing indicator in Redis and broadcasts to channel subscribers.
    """
    channel = event.channel
    user_id = connection.principal.user_id

    # Verify user is subscribed to this channel
    if channel not in connection.subscriptions:
        await manager.send_to_connection(connection, WSError(
            code="NOT_SUBSCRIBED",
            message=f"Not subscribed to channel: {channel}"
        ).model_dump())
        return

    # Get user's display name
    user_name = await _get_user_display_name(user_id)

    # Set typing indicator in Redis (with TTL)
    await typing_tracker.set_typing(user_id, channel, user_name)

    # Broadcast typing update to channel (via Redis pub/sub for multi-instance)
    # Note: typing events use flat structure (not nested under 'data')
    redis_client = await get_redis_client()
    await redis_client.publish(
        f"{CHANNEL_PREFIX}{channel}",
        json.dumps({
            "type": "typing:update",
            "channel": channel,
            "user_id": user_id,
            "user_name": user_name,
            "is_typing": True
        })
    )


async def handle_typing_stop(connection: Connection, event: WSTypingStop):
    """
    Handle typing stop event.

    Removes typing indicator and broadcasts to channel subscribers.
    """
    channel = event.channel
    user_id = connection.principal.user_id

    # Verify user is subscribed to this channel
    if channel not in connection.subscriptions:
        return  # Silently ignore if not subscribed

    # Stop typing indicator
    await typing_tracker.stop_typing(user_id, channel)

    # Broadcast typing update (flat structure, not nested under 'data')
    redis_client = await get_redis_client()
    await redis_client.publish(
        f"{CHANNEL_PREFIX}{channel}",
        json.dumps({
            "type": "typing:update",
            "channel": channel,
            "user_id": user_id,
            "user_name": None,
            "is_typing": False
        })
    )


async def handle_read_mark(connection: Connection, event: WSReadMark):
    """
    Handle read mark event.

    Marks message as read and broadcasts read receipt (only for submission_group scope).
    """
    channel = event.channel
    message_id = event.message_id
    user_id = connection.principal.user_id

    logger.debug(f"read:mark received - channel: {channel}, message_id: {message_id}, user_id: {user_id}")

    # Verify user is subscribed to this channel
    if channel not in connection.subscriptions:
        logger.warning(f"read:mark rejected - user {user_id} not subscribed to {channel}")
        await manager.send_to_connection(connection, WSError(
            code="NOT_SUBSCRIBED",
            message=f"Not subscribed to channel: {channel}"
        ).model_dump())
        return

    # Mark message as read in database
    try:
        with get_db_session() as db:
            cache = get_cache()
            mark_message_as_read(message_id, connection.principal, db, cache)
        logger.info(f"Message {message_id} marked as read by user {user_id}")
    except Exception as e:
        logger.error(f"Failed to mark message {message_id} as read: {e}")
        await manager.send_to_connection(connection, WSError(
            code="READ_MARK_FAILED",
            message=f"Failed to mark message as read: {str(e)}"
        ).model_dump())
        return

    # Only broadcast read receipts for submission_group scope
    if channel.startswith("submission_group:"):
        # Use flat structure (not nested under 'data')
        redis_client = await get_redis_client()
        await redis_client.publish(
            f"{CHANNEL_PREFIX}{channel}",
            json.dumps({
                "type": "read:update",
                "channel": channel,
                "message_id": message_id,
                "user_id": user_id
            })
        )
        logger.debug(f"read:update broadcast sent for message {message_id}")


async def handle_ping(connection: Connection):
    """
    Handle keep-alive ping.

    Responds with pong and refreshes presence.
    """
    # Refresh presence
    await manager.refresh_presence(connection.principal.user_id)

    # Send pong
    await manager.send_to_connection(connection, WSPong(
        timestamp=datetime.now(timezone.utc)
    ).model_dump(mode="json"))


async def handle_reauth(connection: Connection, event: WSReauth):
    """
    Re-arm a live connection with a freshly issued credential (issue #257).

    This is the escape hatch from the close/reconnect cycle: warned by
    ``system:auth_expiring``, a client refreshes its session and sends the new
    token here, so the connection keeps its subscriptions instead of dropping
    and re-establishing all of them a minute later.

    The new credential must belong to the same user. A socket is not a place to
    change identity: its subscriptions were authorised against the principal
    that opened it, and swapping that principal underneath them would hand the
    new user everything the old one was already listening to. A mismatch is
    therefore treated as a failed re-authentication and closes the connection.
    """
    try:
        principal, credential = await authenticate_websocket_token(event.token)
    except WebSocketAuthError as e:
        logger.info(
            f"WebSocket reauth rejected for user={connection.principal.user_id}: {e.reason}"
        )
        await _reject_reauth(connection, e.reason)
        return

    if str(principal.user_id) != str(connection.principal.user_id):
        logger.warning(
            "WebSocket reauth identity mismatch: connection user="
            f"{connection.principal.user_id}, token user={principal.user_id}"
        )
        await _reject_reauth(connection, "Token belongs to a different user")
        return

    connection.credential = credential
    logger.info(
        f"WebSocket reauthenticated: user={principal.user_id} expires_at={credential.expires_at}"
    )
    await manager.send_to_connection(connection, WSReauthed(
        user_id=str(principal.user_id),
        expires_at=credential.expires_at,
    ).model_dump(mode="json"))


async def _reject_reauth(connection: Connection, reason: str):
    """
    A reauth attempt failed — say so, then close.

    Closing with the token-expired code rather than leaving the socket up keeps
    the client on one path: the connection it is holding is not authenticated
    any more, so it must go back through the handshake with a credential the
    user actually has.
    """
    await manager.send_to_connection(connection, WSError(
        code="REAUTH_FAILED",
        message=reason,
    ).model_dump())
    try:
        await connection.websocket.close(code=WS_CLOSE_TOKEN_EXPIRED, reason=reason)
    except Exception:
        # Best-effort: the peer may already be gone.
        logger.debug("Failed to close WebSocket after rejected reauth", exc_info=True)


async def _get_user_display_name(user_id: str) -> Optional[str]:
    """Get user's display name from database."""
    with get_db_session() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            if user.given_name and user.family_name:
                return f"{user.given_name} {user.family_name}"
            return user.given_name or user.family_name or user.email
    return None
