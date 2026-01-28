"""
WebSocket router and endpoint.

Provides the FastAPI WebSocket endpoint for real-time communication.
"""

import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from computor_backend.settings import settings
from computor_backend.websocket.auth import authenticate_websocket_token, WebSocketAuthError
from computor_backend.websocket.connection_manager import manager, ConnectionLimitError
from computor_backend.websocket.handlers import handle_client_message
from computor_types.websocket import WSConnected, WSError

logger = logging.getLogger(__name__)

ws_router = APIRouter()


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

    Server -> Client Events:
        - system:connected: Connection established
        - channel:subscribed: Subscription confirmed
        - channel:unsubscribed: Unsubscription confirmed
        - channel:error: Subscription failed
        - message:new: New message in subscribed channel
        - message:update: Message updated
        - message:delete: Message deleted
        - typing:update: Typing status changed
        - read:update: Read receipt (submission_group only)
        - system:pong: Keep-alive response
        - system:error: Error occurred

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

    try:
        # Authenticate
        principal = await authenticate_websocket_token(token)

        # Register connection
        connection = await manager.connect(websocket, principal)

        # Send connected confirmation
        await manager.send_to_connection(connection, WSConnected(
            user_id=principal.user_id
        ).model_dump())

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
            pass

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
            pass

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close(code=1011, reason="Internal error")
        except Exception:
            pass

    finally:
        if connection:
            await manager.disconnect(connection)
