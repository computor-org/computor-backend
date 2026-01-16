"""
WebSocket event handlers.

Handles incoming client events and dispatches appropriate actions.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from computor_backend.database import get_db
from computor_backend.model.auth import User
from computor_backend.websocket.connection_manager import Connection, manager
from computor_backend.websocket.pubsub import pubsub, typing_tracker
from computor_backend.business_logic.messages import mark_message_as_read
from computor_backend.redis_cache import get_cache
from computor_types.websocket import (
    parse_client_event,
    WSChannelSubscribe,
    WSChannelUnsubscribe,
    WSTypingStart,
    WSTypingStop,
    WSReadMark,
    WSPing,
    WSChannelSubscribed,
    WSChannelUnsubscribed,
    WSChannelError,
    WSTypingUpdate,
    WSReadUpdate,
    WSPong,
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
    with next(get_db()) as db:
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
    await pubsub.publish(channel, "typing:update", {
        "channel": channel,
        "user_id": user_id,
        "user_name": user_name,
        "is_typing": True
    })


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

    # Broadcast typing update
    await pubsub.publish(channel, "typing:update", {
        "channel": channel,
        "user_id": user_id,
        "user_name": None,
        "is_typing": False
    })


async def handle_read_mark(connection: Connection, event: WSReadMark):
    """
    Handle read mark event.

    Marks message as read and broadcasts read receipt (only for submission_group scope).
    """
    channel = event.channel
    message_id = event.message_id
    user_id = connection.principal.user_id

    # Verify user is subscribed to this channel
    if channel not in connection.subscriptions:
        await manager.send_to_connection(connection, WSError(
            code="NOT_SUBSCRIBED",
            message=f"Not subscribed to channel: {channel}"
        ).model_dump())
        return

    # Mark message as read in database
    with next(get_db()) as db:
        cache = get_cache()
        mark_message_as_read(message_id, connection.principal, db, cache)

    # Only broadcast read receipts for submission_group scope
    if channel.startswith("submission_group:"):
        await pubsub.publish(channel, "read:update", {
            "channel": channel,
            "message_id": message_id,
            "user_id": user_id
        })


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


async def _get_user_display_name(user_id: str) -> Optional[str]:
    """Get user's display name from database."""
    with next(get_db()) as db:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            if user.given_name and user.family_name:
                return f"{user.given_name} {user.family_name}"
            return user.given_name or user.family_name or user.username
    return None
