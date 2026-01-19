"""
WebSocket Broadcast Service.

Provides an interface for REST API endpoints to broadcast events
to WebSocket subscribers via Redis pub/sub.

Supports hierarchical broadcasting: events are broadcast to both
the specific target channel AND parent channels (e.g., course).
This allows subscribers to listen at different levels of granularity.
"""

import logging
from typing import Optional, List

from computor_backend.websocket.pubsub import pubsub
from computor_types.messages import MessageTargetProtocol

logger = logging.getLogger(__name__)


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

    async def message_created(self, message: MessageTargetProtocol, message_data: dict):
        """
        Broadcast a new message event to all relevant channels.

        Broadcasts to both the specific target channel AND parent channels
        (hierarchical broadcasting). For example, a message in submission_group:123
        will also be broadcast to course:456 if course_id is set.

        Args:
            message: The Message model instance or MessageGet DTO
            message_data: Serialized message data (MessageGet.model_dump())
        """
        channels = self._get_message_channels(message)
        if not channels:
            logger.warning("No channel determined for message")
            return

        logger.warning(f"Broadcasting message:new to channels: {channels}")
        primary_channel = channels[0]  # Most specific channel
        for channel in channels:
            await self.publish(channel, "message:new", {
                "channel": primary_channel,  # Always reference the primary channel
                "data": message_data
            })

    async def message_updated(self, message: MessageTargetProtocol, message_data: dict, message_id: str):
        """
        Broadcast a message update event to all relevant channels.

        Args:
            message: The Message model instance or MessageGet DTO
            message_data: Serialized message data (MessageGet.model_dump())
            message_id: The message ID
        """
        channels = self._get_message_channels(message)
        if not channels:
            return

        primary_channel = channels[0]
        for channel in channels:
            await self.publish(channel, "message:update", {
                "channel": primary_channel,
                "message_id": message_id,
                "data": message_data
            })

    async def message_deleted(self, message: MessageTargetProtocol, message_id: str):
        """
        Broadcast a message deletion event to all relevant channels.

        Args:
            message: The Message model instance or MessageGet DTO (before deletion)
            message_id: The message ID
        """
        channels = self._get_message_channels(message)
        if not channels:
            return

        primary_channel = channels[0]
        for channel in channels:
            await self.publish(channel, "message:delete", {
                "channel": primary_channel,
                "message_id": message_id
            })

    def _get_message_channels(self, message: MessageTargetProtocol) -> List[str]:
        """
        Determine all WebSocket channels for a message (hierarchical broadcasting).

        Returns channels from most specific to least specific. Events are broadcast
        to ALL returned channels, allowing subscribers at different levels to receive
        notifications.

        Hierarchy (most specific first):
        1. submission_group_id → also broadcasts to course if course_id is set
        2. course_content_id → also broadcasts to course if course_id is set
        3. course_group_id → also broadcasts to course if course_id is set
        4. course_id
        5. course_family_id
        6. organization_id

        Args:
            message: The Message model instance or DTO

        Returns:
            List of channel names (most specific first), empty if no suitable target
        """
        channels: List[str] = []

        # Most specific targets first
        if message.submission_group_id:
            channels.append(f"submission_group:{message.submission_group_id}")

        if message.course_content_id:
            channels.append(f"course_content:{message.course_content_id}")

        if message.course_group_id:
            channels.append(f"course_group:{message.course_group_id}")

        # Course level - add if set (enables hierarchical notifications)
        if message.course_id:
            channels.append(f"course:{message.course_id}")

        # Higher levels
        if message.course_family_id:
            channels.append(f"course_family:{message.course_family_id}")

        if message.organization_id:
            channels.append(f"organization:{message.organization_id}")

        # Remove duplicates while preserving order (most specific first)
        seen = set()
        unique_channels = []
        for ch in channels:
            if ch not in seen:
                seen.add(ch)
                unique_channels.append(ch)

        return unique_channels


# Singleton instance
ws_broadcast = WebSocketBroadcast()
