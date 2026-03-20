"""
WebSocket package for real-time communication.

This package provides a general-purpose WebSocket infrastructure with:
- Connection management with Redis pub/sub for multi-instance support
- Bearer token authentication (reuses existing SSO auth)
- Channel-based subscription model
- Event routing system

Current features:
- Messaging: real-time message events, typing indicators, read receipts
- Deployments: deployment status change, assignment, and unassignment events
- Course: course content mutation events
"""

from computor_backend.websocket.connection_manager import ConnectionManager, manager, ws_metrics
from computor_backend.websocket.broadcast import WebSocketBroadcast, ws_broadcast
from computor_backend.websocket.event_publisher import (
    publish_deployment_status_changed,
    publish_deployment_assigned,
    publish_deployment_unassigned,
    publish_course_content_updated,
)

__all__ = [
    "ConnectionManager",
    "manager",
    "ws_metrics",
    "WebSocketBroadcast",
    "ws_broadcast",
    # Sync event publishers (for Temporal activities and background tasks)
    "publish_deployment_status_changed",
    "publish_deployment_assigned",
    "publish_deployment_unassigned",
    "publish_course_content_updated",
]
