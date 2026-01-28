"""
WebSocket package for real-time communication.

This package provides a general-purpose WebSocket infrastructure with:
- Connection management with Redis pub/sub for multi-instance support
- Bearer token authentication (reuses existing SSO auth)
- Channel-based subscription model
- Event routing system

Current features:
- Messaging: real-time message events, typing indicators, read receipts
"""

from computor_backend.websocket.connection_manager import ConnectionManager, manager, ws_metrics
from computor_backend.websocket.broadcast import WebSocketBroadcast, ws_broadcast

__all__ = [
    "ConnectionManager",
    "manager",
    "ws_metrics",
    "WebSocketBroadcast",
    "ws_broadcast",
]
