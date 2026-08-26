"""
WebSocket router and endpoint.

Provides the FastAPI WebSocket endpoint for real-time communication.
"""

import asyncio
import datetime
import json
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from computor_backend.settings import settings
from computor_backend.websocket.auth import (
    authenticate_websocket_token,
    current_credential_expiry,
    WebSocketAuthError,
    WS_CLOSE_TOKEN_EXPIRED,
)
from computor_backend.websocket.connection_manager import Connection, manager, ConnectionLimitError
from computor_backend.websocket.handlers import handle_client_message
from computor_types.websocket import WSAuthExpiring, WSConnected, WSError

logger = logging.getLogger(__name__)

ws_router = APIRouter()

#: How long before a credential dies the client is told, so it has room to
#: refresh and answer ``system:reauth`` instead of being closed.
EXPIRY_WARNING_LEAD_SECONDS = 60

#: Upper bound on how long the watchdog sleeps between re-reads. SSO TTLs
#: slide, so a deadline resolved once is only a floor; re-reading on this
#: cadence is what lets an active user hold a socket open past its original
#: deadline while an idle one still closes on time.
EXPIRY_RECHECK_INTERVAL_SECONDS = 30


async def _watch_credential_expiry(connection: Connection) -> None:
    """
    Close a connection the moment its credential dies (issue #257).

    Runs beside the receive loop for the life of the connection. Without it the
    only thing that ever noticed an expired token was the client's next HTTP
    call: the socket stayed open, kept delivering events, and reported itself
    healthy while every request beside it came back 401 — the exact split state
    the production report described.

    The loop re-reads the deadline on every wake rather than trusting the one
    from the handshake, because two things move it: an SSO session's sliding
    TTL, and a successful ``system:reauth`` replacing the credential outright.

    Shortly before the deadline the client is warned once (``system:auth_expiring``)
    so it can refresh in place. If it does not, the connection is closed with
    :data:`WS_CLOSE_TOKEN_EXPIRED` — a code of its own, so the client can tell
    "refresh and come back" apart from "your token was rejected".
    """
    warned_for: Optional[datetime.datetime] = None

    while True:
        credential = connection.credential
        if credential is None:
            return

        try:
            expires_at = await current_credential_expiry(credential)
        except WebSocketAuthError as e:
            await _close_expired(connection, e.reason)
            return
        except Exception as e:
            # A Redis blip must not take a healthy connection down. Back off
            # and re-read; the HTTP path still enforces auth in the meantime.
            logger.warning(f"Could not re-read credential expiry, retrying: {e}")
            await asyncio.sleep(EXPIRY_RECHECK_INTERVAL_SECONDS)
            continue

        if expires_at is None:
            # Nothing to watch — a token minted without an expiry, or a session
            # key without a TTL. Leave the connection alone rather than
            # inventing a deadline for it.
            return

        credential.expires_at = expires_at
        remaining = (expires_at - datetime.datetime.now(datetime.timezone.utc)).total_seconds()

        if remaining <= 0:
            await _close_expired(connection, "Token expired")
            return

        if remaining <= EXPIRY_WARNING_LEAD_SECONDS and warned_for != expires_at:
            warned_for = expires_at
            await manager.send_to_connection(connection, WSAuthExpiring(
                expires_at=expires_at,
                seconds_remaining=int(remaining),
            ).model_dump(mode="json"))

        sleep_for = min(remaining, EXPIRY_RECHECK_INTERVAL_SECONDS)
        if remaining > EXPIRY_WARNING_LEAD_SECONDS:
            # Do not sleep past the warning point, or the client loses the
            # window it needs to refresh in place.
            sleep_for = min(sleep_for, remaining - EXPIRY_WARNING_LEAD_SECONDS)
        await asyncio.sleep(max(sleep_for, 0.1))


async def _close_expired(connection: Connection, reason: str) -> None:
    """Tell the client why, then close with the token-expired code."""
    logger.info(
        f"WebSocket credential expired: user={connection.principal.user_id} reason={reason}"
    )
    try:
        await manager.send_to_connection(connection, WSError(
            code="TOKEN_EXPIRED",
            message=reason,
        ).model_dump())
        await connection.websocket.close(code=WS_CLOSE_TOKEN_EXPIRED, reason=reason)
    except Exception:
        # Best-effort: the peer may already be gone. The receive loop's
        # disconnect branch cleans up either way.
        logger.debug("Failed to close expired WebSocket", exc_info=True)


@ws_router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="Bearer token for authentication"),
):
    """
    Main WebSocket endpoint for real-time communication.

    Authentication:
        Pass the bearer token as a query parameter.
        Example: ws://localhost:8000/ws?token=<your_bearer_token>

    Connection Flow:
        1. Client connects with token
        2. Server validates token and accepts connection
        3. Server sends system:connected event with user info
        4. Client subscribes to channels via channel:subscribe
        5. Server validates permissions and confirms with channel:subscribed
        6. Client/server exchange events

    Client -> Server Events:
        - channel:subscribe: Subscribe to channels
          {"type": "channel:subscribe", "channels": ["submission_group:123"]}

        - channel:unsubscribe: Unsubscribe from channels
          {"type": "channel:unsubscribe", "channels": ["submission_group:123"]}

        - typing:start: User started typing
          {"type": "typing:start", "channel": "submission_group:123"}

        - typing:stop: User stopped typing
          {"type": "typing:stop", "channel": "submission_group:123"}

        - read:mark: Mark message as read
          {"type": "read:mark", "channel": "submission_group:123", "message_id": "..."}

        - system:ping: Keep-alive ping
          {"type": "system:ping"}

        - system:reauth: Re-arm this connection with a fresh credential
          {"type": "system:reauth", "token": "..."}

    Server -> Client Events:
        - system:connected: Connection established (carries expires_at)
        - channel:subscribed: Subscription confirmed
        - channel:unsubscribed: Unsubscription confirmed
        - channel:error: Subscription failed
        - message:new: New message in subscribed channel
        - message:update: Message updated
        - message:delete: Message deleted
        - typing:update: Typing status changed
        - read:update: Read receipt (submission_group only)
        - system:pong: Keep-alive response
        - system:auth_expiring: Credential expires shortly — refresh and send system:reauth
        - system:reauthed: A system:reauth was accepted; carries the new expires_at
        - system:error: Error occurred

    Close Codes:
        - 4001: the credential was rejected at handshake — the client needs a new one
        - 4003: the credential that opened this connection has since expired
          (issue #257). Distinct from 4001 on purpose: a client should answer
          this one with a silent session refresh and a reconnect, and only ask
          the user to sign in again once that fails.
        - 4008: connection limit reached
        - 1011: internal error

    Channel Format:
        Channels follow the pattern: {scope}:{id}
        Supported scopes:
        - submission_group: Messages in a submission group
        - course_content: Messages for course content
        - course: Course-level messages

    Keep-Alive:
        Send system:ping every 25 seconds to maintain connection.
        Server responds with system:pong.
        Presence is tracked with 30-second TTL.
    """
    connection = None
    expiry_watchdog = None

    try:
        # Authenticate
        principal, credential = await authenticate_websocket_token(token)

        # Register connection
        connection = await manager.connect(websocket, principal)
        connection.credential = credential

        # Send connected confirmation
        await manager.send_to_connection(connection, WSConnected(
            user_id=principal.user_id,
            expires_at=credential.expires_at,
        ).model_dump(mode="json"))

        # Watch the credential for the life of the connection (issue #257) —
        # the receive loop below never revisits auth, so without this a socket
        # outlives the token that opened it.
        expiry_watchdog = asyncio.create_task(_watch_credential_expiry(connection))

        # Main message loop
        # Note: We don't use a hard timeout here because:
        # 1. WebSocket protocol-level ping/pong keeps the connection alive
        # 2. The underlying websocket library handles ping/pong automatically
        # 3. Long-lived connections (e.g., AI agents) should stay open indefinitely
        # 4. Dead connections are detected when send fails or client disconnects
        while True:
            try:
                # receive() handles all message types including ping/pong
                message = await websocket.receive()

                if message["type"] == "websocket.receive":
                    # Text message - parse as JSON
                    if "text" in message:
                        try:
                            data = json.loads(message["text"])
                            await handle_client_message(connection, data)
                        except json.JSONDecodeError as e:
                            logger.warning(f"WebSocket invalid JSON from user={principal.user_id}: {e}")
                            await manager.send_to_connection(connection, WSError(
                                code="INVALID_JSON",
                                message="Message must be valid JSON"
                            ).model_dump())
                    # Binary messages are typically ping/pong at protocol level
                    # They're handled automatically by the websocket library

                elif message["type"] == "websocket.disconnect":
                    logger.info(f"WebSocket disconnected: user={principal.user_id}")
                    break

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: user={principal.user_id}")
                break

    except WebSocketAuthError as e:
        logger.warning(f"WebSocket auth failed: {e.reason}")
        # Send error before closing
        try:
            await websocket.accept()
            await websocket.send_json(WSError(
                code="AUTH_FAILED",
                message=e.reason
            ).model_dump())
            await websocket.close(code=e.code, reason=e.reason)
        except Exception:
            # Best-effort close: original error already logged; the close
            # itself can fail if the socket is already gone. Nothing to do.
            logger.debug("Failed to close WebSocket after error", exc_info=True)

    except ConnectionLimitError as e:
        logger.warning(f"WebSocket connection limit: {e.message}")
        try:
            await websocket.accept()
            await websocket.send_json(WSError(
                code="CONNECTION_LIMIT",
                message=e.message
            ).model_dump())
            await websocket.close(code=e.code, reason=e.message)
        except Exception:
            # Best-effort close: original error already logged; the close
            # itself can fail if the socket is already gone. Nothing to do.
            logger.debug("Failed to close WebSocket after error", exc_info=True)

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close(code=1011, reason="Internal error")
        except Exception:
            # Best-effort close: original error already logged; the close
            # itself can fail if the socket is already gone. Nothing to do.
            logger.debug("Failed to close WebSocket after error", exc_info=True)

    finally:
        if expiry_watchdog:
            expiry_watchdog.cancel()
        if connection:
            await manager.disconnect(connection)
