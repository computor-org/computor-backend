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
