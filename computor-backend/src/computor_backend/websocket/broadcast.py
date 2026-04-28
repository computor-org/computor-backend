"""
WebSocket Broadcast Service.

Provides an interface for REST API endpoints to broadcast events
to WebSocket subscribers via Redis pub/sub.

Channel model
-------------

Each message event fans out to two kinds of channels:

1. **Scope channel** (e.g. ``submission_group:<id>``, ``course:<id>``)
   — derived from the message's single target column. UI views (a
   per-course dashboard, a submission-group thread, etc.) subscribe to
   the scope they're rendering.

2. **Per-user inbox channels** (``user:<recipient_id>``) — every user
   in the message's read audience receives the same event on their
   personal channel. Connections auto-subscribe to their own
   ``user:<own_id>`` on connect, so the inbox UI just listens once and
   gets every message it has access to without having to enumerate
   every scope the user belongs to.

Global messages (no targets) skip per-user fanout and publish to a
fixed ``global`` channel that every connection is auto-subscribed to.

Cross-scope hierarchical fanout (e.g. submission-group messages also
publishing to ``course:<id>``) used to exist but was removed when the
single-target invariant landed — recipients now get cross-scope
visibility via their per-user channel instead, which is privacy-safe
(no risk of leaking group-private messages to anyone subscribed to the
broader course channel).
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.orm import Session

from computor_backend.websocket.pubsub import pubsub
from computor_types.messages import MessageTargetProtocol

logger = logging.getLogger(__name__)


GLOBAL_CHANNEL = "global"


class WebSocketBroadcast:
    """
    Service for broadcasting events from REST API to WebSocket subscribers.

    Usage in API endpoints:
        from computor_backend.websocket import ws_broadcast

        # After creating a message — db is required to compute the
        # per-recipient inbox fanout.
        await ws_broadcast.message_created(message, payload_dict, db=db)

        # After updating a message
        await ws_broadcast.message_updated(message, payload_dict, message_id, db=db)

        # After deleting a message
        await ws_broadcast.message_deleted(message, message_id, db=db)

        # After marking read/unread
        await ws_broadcast.read_updated(message, message_id, user_id, is_read=True)
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

    async def message_created(
        self,
        message: MessageTargetProtocol,
        message_data: dict,
        db: Session,
    ):
        """Broadcast a new message to its scope channel and to every recipient's
        per-user inbox channel (or to the global channel for global messages).

        Args:
            message: The Message row (or MessageGet DTO with target columns).
            message_data: Serialized payload for clients (``MessageGet.model_dump()``).
            db: DB session — required to compute the recipient audience.
        """
        channels = self._get_all_channels(message, db)
        if not channels:
            logger.warning("No channel determined for message")
            return

        primary_channel = channels[0]
        for channel in channels:
            await self.publish(channel, "message:new", {
                "channel": primary_channel,
                "data": message_data,
            })

    async def message_updated(
        self,
        message: MessageTargetProtocol,
        message_data: dict,
        message_id: str,
        db: Session,
    ):
        """Broadcast a message update. Audience matches ``message_created``."""
        channels = self._get_all_channels(message, db)
        if not channels:
            return

        primary_channel = channels[0]
        for channel in channels:
            await self.publish(channel, "message:update", {
                "channel": primary_channel,
                "message_id": message_id,
                "data": message_data,
            })

    async def message_deleted(
        self,
        message: MessageTargetProtocol,
        message_id: str,
        db: Session,
    ):
        """Broadcast a message deletion. Audience matches ``message_created``."""
        channels = self._get_all_channels(message, db)
        if not channels:
            return

        primary_channel = channels[0]
        for channel in channels:
            await self.publish(channel, "message:delete", {
                "channel": primary_channel,
                "message_id": message_id,
            })

    async def read_updated(
        self,
        message: MessageTargetProtocol,
        message_id: str,
        user_id: str,
        *,
        is_read: bool,
    ):
        """Broadcast a read/unread state change.

        Fires on the message's scope channel (so other recipients update
        their unread badges) AND on the reader's own ``user:<id>`` channel
        (so other tabs / devices of the same user stay in sync).

        Uses a flat payload (``type`` at top level, no nested ``data``) for
        backwards compatibility with the existing WebSocket client handler.
        """
        from computor_backend.websocket.pubsub import CHANNEL_PREFIX
        from computor_backend.redis_cache import get_redis_client
        import json

        scope_channels = self._get_message_channels(message)
        if not scope_channels:
            scope_channels = [GLOBAL_CHANNEL]
        channels = scope_channels + [f"user:{user_id}"]

        redis_client = await get_redis_client()
        for channel in channels:
            await redis_client.publish(
                f"{CHANNEL_PREFIX}{channel}",
                json.dumps({
                    "type": "read:update",
                    "channel": channel,
                    "message_id": message_id,
                    "user_id": user_id,
                    "read": is_read,
                }),
            )
        logger.debug(
            f"Broadcast read:update (read={is_read}) to {channels} for message {message_id}"
        )

    # =========================================================================
    # Deployment events
    # =========================================================================

    async def deployment_status_changed(
        self,
        course_id: str,
        course_content_id: str,
        deployment_id: str,
        previous_status: str,
        new_status: str,
        version_tag: Optional[str] = None,
        example_identifier: Optional[str] = None,
        deployment_message: Optional[str] = None,
        deployed_at: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ):
        """Broadcast deployment status transition to course channel."""
        channel = f"course:{course_id}"
        await self.publish(channel, "deployment:status_changed", {
            "channel": channel,
            "course_id": course_id,
            "course_content_id": course_content_id,
            "deployment_id": deployment_id,
            "previous_status": previous_status,
            "new_status": new_status,
            "version_tag": version_tag,
            "example_identifier": example_identifier,
            "deployment_message": deployment_message,
            "deployed_at": deployed_at,
            "workflow_id": workflow_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    async def deployment_assigned(
        self,
        course_id: str,
        course_content_id: str,
        deployment_id: str,
        version_tag: str,
        deployment_status: str,
        example_identifier: Optional[str] = None,
    ):
        """Broadcast example assignment to course channel."""
        channel = f"course:{course_id}"
        await self.publish(channel, "deployment:assigned", {
            "channel": channel,
            "course_id": course_id,
            "course_content_id": course_content_id,
            "deployment_id": deployment_id,
            "example_identifier": example_identifier,
            "version_tag": version_tag,
            "deployment_status": deployment_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    async def deployment_unassigned(
        self,
        course_id: str,
        course_content_id: str,
        previous_example_identifier: Optional[str] = None,
        previous_version_tag: Optional[str] = None,
    ):
        """Broadcast example unassignment to course channel."""
        channel = f"course:{course_id}"
        await self.publish(channel, "deployment:unassigned", {
            "channel": channel,
            "course_id": course_id,
            "course_content_id": course_content_id,
            "previous_example_identifier": previous_example_identifier,
            "previous_version_tag": previous_version_tag,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    async def course_content_updated(
        self,
        course_id: str,
        course_content_id: str,
        change_type: str,
    ):
        """Broadcast course content mutation to course channel."""
        channel = f"course:{course_id}"
        await self.publish(channel, "course:content_updated", {
            "channel": channel,
            "course_id": course_id,
            "course_content_id": course_content_id,
            "change_type": change_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    # =========================================================================
    # Message channel resolution
    # =========================================================================

    def _get_message_channels(self, message: MessageTargetProtocol) -> List[str]:
        """Scope channel(s) for the message — derived from its target columns.

        With single-target enforcement at the create boundary, every
        message has at most one target column set, so this normally
        returns a single-element list. The list is still ordered
        most-specific to least-specific to keep the API resilient if
        legacy multi-target rows show up. Returns ``[]`` for global
        messages (no targets) — the broadcast layer handles those by
        publishing to the dedicated ``GLOBAL_CHANNEL``.
        """
        channels: List[str] = []
        if message.submission_group_id:
            channels.append(f"submission_group:{message.submission_group_id}")
        if message.course_content_id:
            channels.append(f"course_content:{message.course_content_id}")
        if message.course_group_id:
            channels.append(f"course_group:{message.course_group_id}")
        if message.course_id:
            channels.append(f"course:{message.course_id}")
        if message.course_family_id:
            channels.append(f"course_family:{message.course_family_id}")
        if message.organization_id:
            channels.append(f"organization:{message.organization_id}")
        # Dedupe defensively while preserving order.
        seen = set()
        unique_channels = []
        for ch in channels:
            if ch not in seen:
                seen.add(ch)
                unique_channels.append(ch)
        return unique_channels

    def _get_all_channels(
        self, message: MessageTargetProtocol, db: Session
    ) -> List[str]:
        """Full broadcast target list: scope + per-recipient inbox + global.

        For global messages (no target columns set), returns just
        ``[GLOBAL_CHANNEL]`` — every connected client is auto-subscribed
        to it, so per-user fanout to N-thousand recipients is skipped.

        For targeted messages, returns the scope channel plus
        ``user:<id>`` for every user in the read audience (computed via
        ``get_message_recipient_user_ids``). The author and every system
        admin are always in that audience.
        """
        scope_channels = self._get_message_channels(message)
        if not scope_channels:
            return [GLOBAL_CHANNEL]

        # Local import — avoids a circular dependency at module import.
        from computor_backend.business_logic.messages import (
            get_message_recipient_user_ids,
        )

        recipients = get_message_recipient_user_ids(message, db)
        return scope_channels + [f"user:{uid}" for uid in sorted(recipients)]


# Singleton instance
ws_broadcast = WebSocketBroadcast()
