"""
WebSocket Connection Manager.

Manages WebSocket connections, subscriptions, and message routing.
Uses Redis pub/sub for multi-instance support.
"""

import asyncio
import json
import logging
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field

from fastapi import WebSocket
from sqlalchemy.orm import Session

from computor_backend.database import get_db
from computor_backend.model.course import CourseMember, SubmissionGroup, SubmissionGroupMember, CourseContent
from computor_backend.permissions.principal import Principal
from computor_backend.redis_cache import get_redis_client
from computor_backend.websocket.pubsub import pubsub, typing_tracker, TYPING_PREFIX

logger = logging.getLogger(__name__)


@dataclass
class Connection:
    """Represents an active WebSocket connection."""
    websocket: WebSocket
    principal: Principal
    subscriptions: Set[str] = field(default_factory=set)


class ConnectionManager:
    """
    Manages WebSocket connections and channel subscriptions.

    Features:
    - Track active connections per user
    - Manage channel subscriptions with permission validation
    - Route messages from Redis pub/sub to local connections
    - Handle presence tracking
    """

    def __init__(self):
        self._connections: Dict[str, List[Connection]] = {}  # user_id -> connections
        self._channel_subscribers: Dict[str, Set[str]] = {}  # channel -> user_ids
        self._running = False

    async def start(self):
        """Start the connection manager and pub/sub listener."""
        if self._running:
            return

        self._running = True

        # Register our handler with pub/sub
        pubsub.register_handler("connection_manager", self._handle_pubsub_message)

        # Start pub/sub listener
        await pubsub.start()
        logger.info("ConnectionManager started")

    async def stop(self):
        """Stop the connection manager and clean up."""
        self._running = False

        # Unregister our handler
        pubsub.unregister_handler("connection_manager")

        # Stop pub/sub listener
        await pubsub.stop()

        # Close all connections
        for user_id, connections in list(self._connections.items()):
            for conn in connections:
                try:
                    await conn.websocket.close()
                except Exception:
                    pass

        self._connections.clear()
        self._channel_subscribers.clear()
        logger.info("ConnectionManager stopped")

    async def connect(self, websocket: WebSocket, principal: Principal) -> Connection:
        """
        Register a new WebSocket connection.

        Args:
            websocket: The WebSocket connection
            principal: Authenticated user principal

        Returns:
            Connection object
        """
        await websocket.accept()

        user_id = principal.user_id
        connection = Connection(websocket=websocket, principal=principal)

        if user_id not in self._connections:
            self._connections[user_id] = []
        self._connections[user_id].append(connection)

        # Set presence in Redis
        redis_client = await get_redis_client()
        await redis_client.setex(f"ws:presence:{user_id}", 30, "online")

        logger.info(f"WebSocket connected: user={user_id}, total_connections={len(self._connections[user_id])}")

        return connection

    async def disconnect(self, connection: Connection):
        """
        Remove a WebSocket connection and clean up subscriptions.

        Args:
            connection: The connection to remove
        """
        user_id = connection.principal.user_id

        # Remove from connections list
        if user_id in self._connections:
            self._connections[user_id] = [
                c for c in self._connections[user_id] if c is not connection
            ]
            if not self._connections[user_id]:
                del self._connections[user_id]

        # Unsubscribe from all channels
        for channel in list(connection.subscriptions):
            await self._unsubscribe_connection(connection, channel)

        # Update presence if no more connections
        if user_id not in self._connections:
            redis_client = await get_redis_client()
            await redis_client.delete(f"ws:presence:{user_id}")

        logger.info(f"WebSocket disconnected: user={user_id}")

    async def subscribe(
        self,
        connection: Connection,
        channels: List[str],
        db: Session,
    ) -> tuple[List[str], List[tuple[str, str]]]:
        """
        Subscribe a connection to channels with permission validation.

        Args:
            connection: The connection
            channels: List of channels to subscribe to
            db: Database session for permission checks

        Returns:
            Tuple of (subscribed_channels, failed_channels_with_reasons)
        """
        subscribed = []
        failed = []

        for channel in channels:
            # Validate permission
            can_access, reason = await self._can_subscribe(
                connection.principal, channel, db
            )

            if not can_access:
                failed.append((channel, reason))
                continue

            # Add to connection's subscriptions
            connection.subscriptions.add(channel)

            # Track in channel -> users mapping
            if channel not in self._channel_subscribers:
                self._channel_subscribers[channel] = set()
            self._channel_subscribers[channel].add(connection.principal.user_id)

            # Subscribe to Redis pub/sub for this channel
            await pubsub.subscribe(channel)

            subscribed.append(channel)
            logger.debug(f"User {connection.principal.user_id} subscribed to {channel}")

        return subscribed, failed

    async def unsubscribe(self, connection: Connection, channels: List[str]) -> List[str]:
        """
        Unsubscribe a connection from channels.

        Args:
            connection: The connection
            channels: List of channels to unsubscribe from

        Returns:
            List of successfully unsubscribed channels
        """
        unsubscribed = []

        for channel in channels:
            if channel in connection.subscriptions:
                await self._unsubscribe_connection(connection, channel)
                unsubscribed.append(channel)

        return unsubscribed

    async def _unsubscribe_connection(self, connection: Connection, channel: str):
        """Internal method to unsubscribe a single connection from a channel."""
        connection.subscriptions.discard(channel)
        user_id = connection.principal.user_id

        # Remove from channel subscribers
        if channel in self._channel_subscribers:
            self._channel_subscribers[channel].discard(user_id)

            # Check if any other connection from this user is still subscribed
            has_other_subscription = False
            if user_id in self._connections:
                for conn in self._connections[user_id]:
                    if channel in conn.subscriptions:
                        has_other_subscription = True
                        break

            if not has_other_subscription:
                self._channel_subscribers[channel].discard(user_id)

            # If no subscribers left, unsubscribe from Redis
            if not self._channel_subscribers[channel]:
                await pubsub.unsubscribe(channel)
                del self._channel_subscribers[channel]

    async def _can_subscribe(
        self,
        principal: Principal,
        channel: str,
        db: Session,
    ) -> tuple[bool, str]:
        """
        Check if a user can subscribe to a channel.

        Args:
            principal: User principal
            channel: Channel name (format: "scope:id")
            db: Database session

        Returns:
            Tuple of (can_subscribe, reason_if_denied)
        """
        parts = channel.split(":", 1)
        if len(parts) != 2:
            return False, "Invalid channel format"

        scope, target_id = parts

        if scope == "submission_group":
            return await self._can_access_submission_group(principal, target_id, db)

        elif scope == "course":
            return await self._can_access_course(principal, target_id, db)

        elif scope == "course_content":
            return await self._can_access_course_content(principal, target_id, db)

        else:
            return False, f"Unknown channel scope: {scope}"

    async def _can_access_submission_group(
        self,
        principal: Principal,
        submission_group_id: str,
        db: Session,
    ) -> tuple[bool, str]:
        """Check if user can access a submission group channel."""
        # Check if user is a submission group member
        is_member = db.query(
            db.query(SubmissionGroupMember.id)
            .join(CourseMember, CourseMember.id == SubmissionGroupMember.course_member_id)
            .filter(
                SubmissionGroupMember.submission_group_id == submission_group_id,
                CourseMember.user_id == principal.user_id
            )
            .exists()
        ).scalar()

        if is_member:
            return True, ""

        # Check if user has elevated role in the course
        submission_group = db.query(SubmissionGroup).filter(
            SubmissionGroup.id == submission_group_id
        ).first()

        if not submission_group:
            return False, "Submission group not found"

        has_elevated_role = db.query(
            db.query(CourseMember.id)
            .filter(
                CourseMember.course_id == submission_group.course_id,
                CourseMember.user_id == principal.user_id,
                CourseMember.course_role_id != "_student"
            )
            .exists()
        ).scalar()

        if has_elevated_role:
            return True, ""

        return False, "Not a member of this submission group"

    async def _can_access_course(
        self,
        principal: Principal,
        course_id: str,
        db: Session,
    ) -> tuple[bool, str]:
        """Check if user can access a course channel."""
        is_member = db.query(
            db.query(CourseMember.id)
            .filter(
                CourseMember.course_id == course_id,
                CourseMember.user_id == principal.user_id
            )
            .exists()
        ).scalar()

        if is_member:
            return True, ""

        return False, "Not a member of this course"

    async def _can_access_course_content(
        self,
        principal: Principal,
        course_content_id: str,
        db: Session,
    ) -> tuple[bool, str]:
        """Check if user can access a course content channel."""
        # Get the course for this content
        course_content = db.query(CourseContent).filter(
            CourseContent.id == course_content_id
        ).first()

        if not course_content:
            return False, "Course content not found"

        # Check course membership
        is_member = db.query(
            db.query(CourseMember.id)
            .filter(
                CourseMember.course_id == course_content.course_id,
                CourseMember.user_id == principal.user_id
            )
            .exists()
        ).scalar()

        if is_member:
            return True, ""

        return False, "Not a member of this course"

    async def _handle_pubsub_message(self, channel: str, data: dict):
        """
        Handle incoming message from Redis pub/sub.

        Routes the message to all local connections subscribed to this channel.

        Args:
            channel: Channel name (without prefix)
            data: Event data
        """
        if channel not in self._channel_subscribers:
            return

        # Get all users subscribed to this channel
        user_ids = self._channel_subscribers.get(channel, set())

        # Send to all connections for each user
        for user_id in user_ids:
            connections = self._connections.get(user_id, [])
            for conn in connections:
                if channel in conn.subscriptions:
                    try:
                        await conn.websocket.send_json(data)
                    except Exception as e:
                        logger.error(f"Failed to send to user {user_id}: {e}")

    async def send_to_user(self, user_id: str, event: dict):
        """
        Send an event directly to a specific user (all their connections).

        Args:
            user_id: Target user ID
            event: Event data to send
        """
        connections = self._connections.get(user_id, [])
        for conn in connections:
            try:
                await conn.websocket.send_json(event)
            except Exception as e:
                logger.error(f"Failed to send to user {user_id}: {e}")

    async def send_to_connection(self, connection: Connection, event: dict):
        """
        Send an event to a specific connection.

        Args:
            connection: Target connection
            event: Event data to send
        """
        try:
            await connection.websocket.send_json(event)
        except Exception as e:
            logger.error(f"Failed to send to connection: {e}")

    async def broadcast_to_channel(self, channel: str, event: dict, exclude_user_id: Optional[str] = None):
        """
        Broadcast an event to all local subscribers of a channel.

        Note: For multi-instance broadcasting, use pubsub.publish() instead.

        Args:
            channel: Channel name
            event: Event data to send
            exclude_user_id: Optional user ID to exclude from broadcast
        """
        user_ids = self._channel_subscribers.get(channel, set())

        for user_id in user_ids:
            if exclude_user_id and user_id == exclude_user_id:
                continue

            connections = self._connections.get(user_id, [])
            for conn in connections:
                if channel in conn.subscriptions:
                    try:
                        await conn.websocket.send_json(event)
                    except Exception as e:
                        logger.error(f"Failed to broadcast to user {user_id}: {e}")

    async def refresh_presence(self, user_id: str):
        """Refresh user's presence TTL."""
        redis_client = await get_redis_client()
        await redis_client.setex(f"ws:presence:{user_id}", 30, "online")

    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return sum(len(conns) for conns in self._connections.values())

    def get_user_count(self) -> int:
        """Get number of unique connected users."""
        return len(self._connections)


# Singleton instance
manager = ConnectionManager()
