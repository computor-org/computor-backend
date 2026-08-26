"""
WebSocket event DTOs for real-time communication.

This module defines the event types for the WebSocket system.
Events follow a namespaced pattern: "namespace:action"

Namespaces:
- system: Core WebSocket operations (ping, pong, error)
- channel: Subscription management (subscribe, unsubscribe)
- message: Message events (new, update, delete)
- typing: Typing indicators (start, stop, update)
- read: Read receipts (mark, update)
- maintenance: Maintenance mode notifications (activated, deactivated, scheduled, cancelled)
- deployment: Deployment state change notifications (status_changed, assigned, unassigned)
- course: Course-level mutation notifications (content_updated)
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional, Any, Union
from datetime import datetime


# =============================================================================
# Base Event Types
# =============================================================================

class WSEventBase(BaseModel):
    """Base class for all WebSocket events."""
    type: str


# =============================================================================
# Client -> Server Events
# =============================================================================

class WSChannelSubscribe(WSEventBase):
    """Subscribe to one or more channels."""
    type: Literal["channel:subscribe"] = "channel:subscribe"
    channels: list[str] = Field(..., description="Channels to subscribe to, e.g., ['submission_group:123']")


class WSChannelUnsubscribe(WSEventBase):
    """Unsubscribe from one or more channels."""
    type: Literal["channel:unsubscribe"] = "channel:unsubscribe"
    channels: list[str] = Field(..., description="Channels to unsubscribe from")


class WSTypingStart(WSEventBase):
    """User started typing in a channel."""
    type: Literal["typing:start"] = "typing:start"
    channel: str = Field(..., description="Channel where user is typing, e.g., 'submission_group:123'")


class WSTypingStop(WSEventBase):
    """User stopped typing in a channel."""
    type: Literal["typing:stop"] = "typing:stop"
    channel: str = Field(..., description="Channel where user stopped typing")


class WSReadMark(WSEventBase):
    """Mark a message as read."""
    type: Literal["read:mark"] = "read:mark"
    channel: str = Field(..., description="Channel the message belongs to")
    message_id: str = Field(..., description="ID of the message to mark as read")


class WSPing(WSEventBase):
    """Keep-alive ping from client."""
    type: Literal["system:ping"] = "system:ping"


class WSReauth(WSEventBase):
    """
    Re-arm a live connection with a fresh credential (issue #257).

    A socket used to outlive the token that opened it: the handshake
    authenticated once and nothing ever revisited it, so HTTP started
    answering 401 while the socket sat there looking healthy. The server now
    closes an expired connection with ``4003``; this event is the way to avoid
    that close entirely — on ``system:auth_expiring`` the client refreshes its
    session and sends the new token here, keeping its subscriptions.

    The new token must belong to the same user; anything else is treated as a
    failed re-authentication, not as a way to change identity mid-connection.
    """
    type: Literal["system:reauth"] = "system:reauth"
    token: str = Field(..., description="Freshly issued session or API token for the same user")


# =============================================================================
# Server -> Client Events
# =============================================================================

class WSChannelSubscribed(WSEventBase):
    """Confirmation of successful subscription."""
    type: Literal["channel:subscribed"] = "channel:subscribed"
    channels: list[str] = Field(..., description="Channels successfully subscribed to")


class WSChannelUnsubscribed(WSEventBase):
    """Confirmation of successful unsubscription."""
    type: Literal["channel:unsubscribed"] = "channel:unsubscribed"
    channels: list[str] = Field(..., description="Channels successfully unsubscribed from")


class WSChannelError(WSEventBase):
    """Subscription error for a specific channel."""
    type: Literal["channel:error"] = "channel:error"
    channel: str = Field(..., description="Channel that failed")
    reason: str = Field(..., description="Error reason")


class WSMessageNew(WSEventBase):
    """New message created in a channel."""
    type: Literal["message:new"] = "message:new"
    channel: str = Field(..., description="Channel the message was posted to")
    data: dict = Field(..., description="Message data (MessageGet serialized)")


class WSMessageUpdate(WSEventBase):
    """Message was updated."""
    type: Literal["message:update"] = "message:update"
    channel: str = Field(..., description="Channel the message belongs to")
    message_id: str = Field(..., description="ID of the updated message")
    data: dict = Field(..., description="Updated message data (MessageGet serialized)")


class WSMessageDelete(WSEventBase):
    """Message was deleted."""
    type: Literal["message:delete"] = "message:delete"
    channel: str = Field(..., description="Channel the message belonged to")
    message_id: str = Field(..., description="ID of the deleted message")


class WSTypingUpdate(WSEventBase):
    """Typing status update for a user in a channel."""
    type: Literal["typing:update"] = "typing:update"
    channel: str = Field(..., description="Channel where typing status changed")
    user_id: str = Field(..., description="ID of the user")
    user_name: Optional[str] = Field(None, description="Display name of the user")
    is_typing: bool = Field(..., description="Whether the user is currently typing")


class WSReadUpdate(WSEventBase):
    """Read receipt notification (only for submission_group scope)."""
    type: Literal["read:update"] = "read:update"
    channel: str = Field(..., description="Channel (submission_group only)")
    message_id: str = Field(..., description="ID of the message that was read")
    user_id: str = Field(..., description="ID of the user who read the message")


class WSPong(WSEventBase):
    """Keep-alive pong response."""
    type: Literal["system:pong"] = "system:pong"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WSError(WSEventBase):
    """General error event."""
    type: Literal["system:error"] = "system:error"
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")


class WSConnected(WSEventBase):
    """Connection established confirmation."""
    type: Literal["system:connected"] = "system:connected"
    user_id: str = Field(..., description="ID of the authenticated user")
    expires_at: Optional[datetime] = Field(
        None,
        description="When the credential behind this connection expires; null when it never does"
    )


class WSAuthExpiring(WSEventBase):
    """
    The credential behind this connection is about to expire (issue #257).

    Sent once per deadline, shortly before it passes, so the client can refresh
    and answer with ``system:reauth`` instead of being closed with ``4003``.
    """
    type: Literal["system:auth_expiring"] = "system:auth_expiring"
    expires_at: datetime = Field(..., description="When the current credential expires")
    seconds_remaining: int = Field(..., description="Seconds left at the moment the warning was sent")


class WSReauthed(WSEventBase):
    """Confirmation that a ``system:reauth`` was accepted and the deadline moved."""
    type: Literal["system:reauthed"] = "system:reauthed"
    user_id: str = Field(..., description="ID of the authenticated user (unchanged)")
    expires_at: Optional[datetime] = Field(
        None,
        description="New expiry of the connection, or null when the new credential never expires"
    )


# =============================================================================
# Maintenance Events (Server -> Client)
# =============================================================================

class WSMaintenanceActivated(WSEventBase):
    """Maintenance mode has been activated."""
    type: Literal["maintenance:activated"] = "maintenance:activated"
    active: bool = True
    message: str = Field(..., description="Maintenance message for users")
    activated_at: str = Field(..., description="ISO8601 timestamp of activation")


class WSMaintenanceDeactivated(WSEventBase):
    """Maintenance mode has been deactivated."""
    type: Literal["maintenance:deactivated"] = "maintenance:deactivated"
    active: bool = False
    message: str = Field(default="Maintenance complete. Full service has been restored.")


class WSMaintenanceScheduled(WSEventBase):
    """Maintenance has been scheduled for a future time."""
    type: Literal["maintenance:scheduled"] = "maintenance:scheduled"
    scheduled_at: str = Field(..., description="ISO8601 datetime of planned maintenance")
    message: str = Field(..., description="Schedule message for users")


class WSMaintenanceCancelled(WSEventBase):
    """Scheduled maintenance has been cancelled."""
    type: Literal["maintenance:cancelled"] = "maintenance:cancelled"
    message: str = Field(default="Scheduled maintenance has been cancelled.")


class WSMaintenanceReminder(WSEventBase):
    """Countdown reminder for upcoming scheduled maintenance."""
    type: Literal["maintenance:reminder"] = "maintenance:reminder"
    minutes_remaining: int = Field(..., description="Minutes until maintenance begins")
    scheduled_at: str = Field(..., description="ISO8601 datetime of planned maintenance")
    message: str = Field(..., description="Maintenance message for users")


# =============================================================================
# Deployment Events (Server -> Client)
# =============================================================================

class WSDeploymentStatusChanged(WSEventBase):
    """Deployment status transition (e.g., pending -> deploying -> deployed/failed)."""
    type: Literal["deployment:status_changed"] = "deployment:status_changed"
    channel: str = Field(..., description="Channel (course:{course_id})")
    course_id: str = Field(..., description="ID of the course")
    course_content_id: str = Field(..., description="ID of the course content")
    deployment_id: str = Field(..., description="ID of the deployment")
    previous_status: str = Field(..., description="Status before the change")
    new_status: str = Field(..., description="Status after the change")
    version_tag: Optional[str] = Field(None, description="Semantic version tag")
    example_identifier: Optional[str] = Field(None, description="Example identifier path")
    deployment_message: Optional[str] = Field(None, description="Error or status message")
    deployed_at: Optional[str] = Field(None, description="ISO8601 timestamp of deployment completion")
    workflow_id: Optional[str] = Field(None, description="Temporal workflow ID")
    timestamp: str = Field(..., description="ISO8601 timestamp of the event")


class WSDeploymentAssigned(WSEventBase):
    """Example was assigned to course content by lecturer."""
    type: Literal["deployment:assigned"] = "deployment:assigned"
    channel: str = Field(..., description="Channel (course:{course_id})")
    course_id: str = Field(..., description="ID of the course")
    course_content_id: str = Field(..., description="ID of the course content")
    deployment_id: str = Field(..., description="ID of the deployment")
    example_identifier: Optional[str] = Field(None, description="Example identifier path")
    version_tag: str = Field(..., description="Semantic version tag")
    deployment_status: str = Field(..., description="Current deployment status")
    timestamp: str = Field(..., description="ISO8601 timestamp of the event")


class WSDeploymentUnassigned(WSEventBase):
    """Example was unassigned from course content by lecturer."""
    type: Literal["deployment:unassigned"] = "deployment:unassigned"
    channel: str = Field(..., description="Channel (course:{course_id})")
    course_id: str = Field(..., description="ID of the course")
    course_content_id: str = Field(..., description="ID of the course content")
    previous_example_identifier: Optional[str] = Field(None, description="Previously assigned example identifier")
    previous_version_tag: Optional[str] = Field(None, description="Previously assigned version tag")
    timestamp: str = Field(..., description="ISO8601 timestamp of the event")


# =============================================================================
# Course Events (Server -> Client)
# =============================================================================

class WSCourseContentUpdated(WSEventBase):
    """Course content was created, updated, or deleted."""
    type: Literal["course:content_updated"] = "course:content_updated"
    channel: str = Field(..., description="Channel (course:{course_id})")
    course_id: str = Field(..., description="ID of the course")
    course_content_id: str = Field(..., description="ID of the course content")
    change_type: str = Field(..., description="Type of change: created, updated, deleted, reordered")
    timestamp: str = Field(..., description="ISO8601 timestamp of the event")


class WSCourseUpdated(WSEventBase):
    """Course-level settings changed.

    Rides the existing ``course:{course_id}`` channel so no new subscription is
    needed. Carries no payload beyond the id: a client refetches the course,
    because a ``visible`` flip (issue #338) can move the entire content tree in
    or out of view rather than changing one row.
    """
    type: Literal["course:updated"] = "course:updated"
    channel: str = Field(..., description="Channel (course:{course_id})")
    course_id: str = Field(..., description="ID of the course")
    change_type: str = Field(..., description="Type of change: updated, visibility_changed")
    timestamp: str = Field(..., description="ISO8601 timestamp of the event")


# =============================================================================
# Union Types for Parsing
# =============================================================================

# All events that can be sent from client to server
ClientEvent = Union[
    WSChannelSubscribe,
    WSChannelUnsubscribe,
    WSTypingStart,
    WSTypingStop,
    WSReadMark,
    WSPing,
    WSReauth,
]

# All events that can be sent from server to client
ServerEvent = Union[
    WSChannelSubscribed,
    WSChannelUnsubscribed,
    WSChannelError,
    WSMessageNew,
    WSMessageUpdate,
    WSMessageDelete,
    WSTypingUpdate,
    WSReadUpdate,
    WSPong,
    WSError,
    WSConnected,
    WSAuthExpiring,
    WSReauthed,
    WSMaintenanceActivated,
    WSMaintenanceDeactivated,
    WSMaintenanceScheduled,
    WSMaintenanceCancelled,
    WSMaintenanceReminder,
    WSDeploymentStatusChanged,
    WSDeploymentAssigned,
    WSDeploymentUnassigned,
    WSCourseContentUpdated,
    WSCourseUpdated,
]


# =============================================================================
# Event Type Registry (for handler dispatch)
# =============================================================================

CLIENT_EVENT_TYPES = {
    "channel:subscribe": WSChannelSubscribe,
    "channel:unsubscribe": WSChannelUnsubscribe,
    "typing:start": WSTypingStart,
    "typing:stop": WSTypingStop,
    "read:mark": WSReadMark,
    "system:ping": WSPing,
    "system:reauth": WSReauth,
}


def parse_client_event(data: dict) -> Optional[ClientEvent]:
    """
    Parse incoming client event data into typed event object.

    Args:
        data: Raw event data from WebSocket

    Returns:
        Parsed event object or None if invalid
    """
    event_type = data.get("type")
    if not event_type or event_type not in CLIENT_EVENT_TYPES:
        return None

    event_class = CLIENT_EVENT_TYPES[event_type]
    try:
        return event_class.model_validate(data)
    except Exception:
        return None
