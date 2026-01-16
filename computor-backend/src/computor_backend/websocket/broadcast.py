"""
WebSocket Broadcast Service.

Provides an interface for REST API endpoints to broadcast events
to WebSocket subscribers via Redis pub/sub.
"""

import logging
from typing import Optional, Any, Union, Protocol

from computor_backend.websocket.pubsub import pubsub

logger = logging.getLogger(__name__)


class MessageLike(Protocol):
    """Protocol for objects that have message target fields."""
    submission_group_id: Optional[str]
    course_content_id: Optional[str]
    course_group_id: Optional[str]
    course_id: Optional[str]
    course_family_id: Optional[str]
    organization_id: Optional[str]


class WebSocketBroadcast:
    """
    Service for broadcasting events from REST API to WebSocket subscribers.

    Usage in API endpoints:
        from computor_backend.websocket import ws_broadcast

        # After creating a message
        await ws_broadcast.message_created(message, db)

        # After updating a message
        await ws_broadcast.message_updated(message, db)

        # After deleting a message
        await ws_broadcast.message_deleted(message_id, channel)
    """

    async def publish(self, channel: str, event_type: str, data: dict):
        """
        Publish an event to a channel.

        This is the low-level method for broadcasting any event.
        Use the higher-level methods (message_created, etc.) when possible.

        Args:
            channel: Channel name (e.g., "submission_group:123")
            event_type: Event type (e.g., "message:new")
            data: Event payload
        """
        await pubsub.publish(channel, event_type, data)
        logger.debug(f"Broadcast {event_type} to {channel}")

    async def message_created(self, message: MessageLike, message_data: dict):
        """
        Broadcast a new message event.

        Determines the appropriate channel from the message's target fields
        and broadcasts the message:new event.

        Args:
            message: The Message model instance or MessageGet DTO
            message_data: Serialized message data (MessageGet.model_dump())
        """
        channel = self._get_message_channel(message)
        if not channel:
            logger.warning(f"No channel determined for message")
            return

        await self.publish(channel, "message:new", {
            "channel": channel,
            "data": message_data
        })

    async def message_updated(self, message: MessageLike, message_data: dict, message_id: str):
        """
        Broadcast a message update event.

        Args:
            message: The Message model instance or MessageGet DTO
            message_data: Serialized message data (MessageGet.model_dump())
            message_id: The message ID
        """
        channel = self._get_message_channel(message)
        if not channel:
            return

        await self.publish(channel, "message:update", {
            "channel": channel,
            "message_id": message_id,
            "data": message_data
        })

    async def message_deleted(self, message: MessageLike, message_id: str):
        """
        Broadcast a message deletion event.

        Args:
            message: The Message model instance or MessageGet DTO (before deletion)
            message_id: The message ID
        """
        channel = self._get_message_channel(message)
        if not channel:
            return

        await self.publish(channel, "message:delete", {
            "channel": channel,
            "message_id": message_id
        })

    def _get_message_channel(self, message: MessageLike) -> Optional[str]:
        """
        Determine the WebSocket channel for a message based on its target.

        Priority order (most specific to least specific):
        1. submission_group_id
        2. course_content_id
        3. course_group_id
        4. course_id
        5. course_family_id
        6. organization_id

        Args:
            message: The Message model instance

        Returns:
            Channel name or None if no suitable target
        """
        if message.submission_group_id:
            return f"submission_group:{message.submission_group_id}"

        if message.course_content_id:
            return f"course_content:{message.course_content_id}"

        if message.course_group_id:
            return f"course_group:{message.course_group_id}"

        if message.course_id:
            return f"course:{message.course_id}"

        if message.course_family_id:
            return f"course_family:{message.course_family_id}"

        if message.organization_id:
            return f"organization:{message.organization_id}"

        # user_id and course_member_id are not currently supported for WebSocket
        return None


# Singleton instance
ws_broadcast = WebSocketBroadcast()
