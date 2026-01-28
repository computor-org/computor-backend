"""
WebSocket Connection Manager.

Manages WebSocket connections, subscriptions, and message routing.
Uses Redis pub/sub for multi-instance support.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field

from fastapi import WebSocket
from sqlalchemy.orm import Session

from computor_backend.database import get_db
from computor_backend.model.course import CourseMember, SubmissionGroup, SubmissionGroupMember, CourseContent
from computor_backend.permissions.principal import Principal
from computor_backend.redis_cache import get_redis_client
from computor_backend.settings import settings
from computor_backend.websocket.pubsub import pubsub, typing_tracker, TYPING_PREFIX

logger = logging.getLogger(__name__)


class WebSocketMetrics:
    """
    Simple metrics tracking for WebSocket connections.

    Tracks connection counts, message counts, and error rates.
    Can be extended with Prometheus or other metrics backends.
    """

    def __init__(self):
        self.total_connections = 0
        self.total_disconnections = 0
        self.total_messages_sent = 0
        self.total_messages_received = 0
        self.total_send_errors = 0
        self.total_send_timeouts = 0
        self.total_connection_limit_hits = 0

    def connection_opened(self):
        """Track a new connection."""
        self.total_connections += 1

    def connection_closed(self):
        """Track a closed connection."""
        self.total_disconnections += 1

    def message_sent(self):
        """Track a successfully sent message."""
        self.total_messages_sent += 1

    def message_received(self):
        """Track a received message."""
        self.total_messages_received += 1

    def send_error(self):
        """Track a send error."""
        self.total_send_errors += 1

    def send_timeout(self):
        """Track a send timeout."""
        self.total_send_timeouts += 1

    def connection_limit_hit(self):
        """Track when connection limit is reached."""
        self.total_connection_limit_hits += 1

    def get_metrics(self) -> dict:
        """Get all metrics as a dictionary."""
        return {
            "total_connections": self.total_connections,
            "total_disconnections": self.total_disconnections,
            "active_connections": self.total_connections - self.total_disconnections,
            "total_messages_sent": self.total_messages_sent,
            "total_messages_received": self.total_messages_received,
            "total_send_errors": self.total_send_errors,
            "total_send_timeouts": self.total_send_timeouts,
            "total_connection_limit_hits": self.total_connection_limit_hits,
            "error_rate": (
                self.total_send_errors / max(self.total_messages_sent, 1)
            ) if self.total_messages_sent > 0 else 0.0
        }


# Global metrics instance
ws_metrics = WebSocketMetrics()


class ConnectionLimitError(Exception):
    """Raised when connection limits are exceeded."""
    def __init__(self, message: str, code: int = 4008):
        self.message = message
        self.code = code
        super().__init__(message)


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
        logger.info("Stopping ConnectionManager...")
        self._running = False

        # Unregister our handler
        pubsub.unregister_handler("connection_manager")

        # Stop pub/sub listener
        await pubsub.stop()

        # Close all connections with timeout
        close_tasks = []
        for user_id, connections in list(self._connections.items()):
            for conn in connections:
                close_tasks.append(self._close_connection_safe(conn))

        if close_tasks:
            # Wait for all close operations with overall timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(*close_tasks, return_exceptions=True),
                    timeout=3.0
                )
            except asyncio.TimeoutError:
                logger.warning(f"Timeout closing {len(close_tasks)} WebSocket connections")

        self._connections.clear()
        self._channel_subscribers.clear()
        logger.info("ConnectionManager stopped")

    async def _close_connection_safe(self, conn: Connection):
        """Close a connection safely with timeout."""
        try:
            await asyncio.wait_for(conn.websocket.close(), timeout=1.0)
        except asyncio.TimeoutError:
            pass
        except Exception:
            pass

    async def connect(self, websocket: WebSocket, principal: Principal) -> Connection:
        """
        Register a new WebSocket connection.

        Args:
            websocket: The WebSocket connection
            principal: Authenticated user principal

        Returns:
            Connection object

        Raises:
            ConnectionLimitError: If connection limits are exceeded
        """
        user_id = principal.user_id

        # Check total connection limit
        total_connections = self.get_connection_count()
        if total_connections >= settings.WS_MAX_TOTAL_CONNECTIONS:
            logger.warning(f"Total connection limit reached: {total_connections}/{settings.WS_MAX_TOTAL_CONNECTIONS}")
            ws_metrics.connection_limit_hit()
            raise ConnectionLimitError(
                f"Server connection limit reached",
                code=4008
            )

        # Check per-user connection limit
        user_connections = len(self._connections.get(user_id, []))
        if user_connections >= settings.WS_MAX_CONNECTIONS_PER_USER:
            logger.warning(f"User {user_id} connection limit reached: {user_connections}/{settings.WS_MAX_CONNECTIONS_PER_USER}")
            ws_metrics.connection_limit_hit()
            raise ConnectionLimitError(
                f"Too many connections (max {settings.WS_MAX_CONNECTIONS_PER_USER})",
                code=4008
            )

        await websocket.accept()

        connection = Connection(websocket=websocket, principal=principal)

        if user_id not in self._connections:
            self._connections[user_id] = []
        self._connections[user_id].append(connection)

        # Set presence in Redis with configurable TTL
        redis_client = await get_redis_client()
        await redis_client.setex(f"ws:presence:{user_id}", settings.WS_PRESENCE_TTL, "online")

        # Track metrics
        ws_metrics.connection_opened()

        logger.info(f"WebSocket connected: user={user_id}, user_connections={len(self._connections[user_id])}, total={self.get_connection_count()}")

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

        # Track metrics
        ws_metrics.connection_closed()

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

    async def _send_with_timeout(self, conn: Connection, data: dict, user_id: str) -> bool:
        """
        Send data to a connection with timeout.

        Args:
            conn: Target connection
            data: Data to send
            user_id: User ID for logging

        Returns:
            True if successful, False otherwise
        """
        try:
            await asyncio.wait_for(
                conn.websocket.send_json(data),
                timeout=settings.WS_SEND_TIMEOUT
            )
            ws_metrics.message_sent()
            return True
        except asyncio.TimeoutError:
            logger.warning(f"Send timeout to user {user_id}")
            ws_metrics.send_timeout()
            return False
        except Exception as e:
            logger.error(f"Failed to send to user {user_id}: {e}")
            ws_metrics.send_error()
            return False

    async def _handle_pubsub_message(self, channel: str, data: dict):
        """
        Handle incoming message from Redis pub/sub.

        Routes the message to all local connections subscribed to this channel.
        Uses concurrent sends for better performance.

        Args:
            channel: Channel name (without prefix)
            data: Event data
        """
        logger.debug(f"Received pubsub message on channel: {channel}")

        if channel not in self._channel_subscribers:
            logger.debug(f"No local subscribers for channel: {channel}")
            return

        # Get all users subscribed to this channel (make a copy to avoid modification during iteration)
        user_ids = set(self._channel_subscribers.get(channel, set()))
        logger.debug(f"Forwarding to {len(user_ids)} users on channel {channel}")

        # Collect all send tasks for concurrent execution
        send_tasks = []
        for user_id in user_ids:
            connections = list(self._connections.get(user_id, []))
            for conn in connections:
                if channel in conn.subscriptions:
                    send_tasks.append(self._send_with_timeout(conn, data, user_id))

        # Execute all sends concurrently
        if send_tasks:
            results = await asyncio.gather(*send_tasks, return_exceptions=True)
            success_count = sum(1 for r in results if r is True)
            logger.debug(f"Broadcast to channel {channel}: {success_count}/{len(send_tasks)} successful")

    async def send_to_user(self, user_id: str, event: dict):
        """
        Send an event directly to a specific user (all their connections).
        Uses concurrent sends for better performance.

        Args:
            user_id: Target user ID
            event: Event data to send
        """
        # Make a copy to avoid modification during iteration
        connections = list(self._connections.get(user_id, []))
        if not connections:
            return

        # Send to all connections concurrently
        send_tasks = [self._send_with_timeout(conn, event, user_id) for conn in connections]
        await asyncio.gather(*send_tasks, return_exceptions=True)

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
        Uses concurrent sends for better performance.

        Note: For multi-instance broadcasting, use pubsub.publish() instead.

        Args:
            channel: Channel name
            event: Event data to send
            exclude_user_id: Optional user ID to exclude from broadcast
        """
        # Make copies to avoid modification during iteration
        user_ids = set(self._channel_subscribers.get(channel, set()))

        # Collect all send tasks for concurrent execution
        send_tasks = []
        for user_id in user_ids:
            if exclude_user_id and user_id == exclude_user_id:
                continue

            connections = list(self._connections.get(user_id, []))
            for conn in connections:
                if channel in conn.subscriptions:
                    send_tasks.append(self._send_with_timeout(conn, event, user_id))

        # Execute all sends concurrently
        if send_tasks:
            await asyncio.gather(*send_tasks, return_exceptions=True)

    async def refresh_presence(self, user_id: str):
        """Refresh user's presence TTL."""
        redis_client = await get_redis_client()
        await redis_client.setex(f"ws:presence:{user_id}", settings.WS_PRESENCE_TTL, "online")

    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return sum(len(conns) for conns in self._connections.values())

    def get_user_count(self) -> int:
        """Get number of unique connected users."""
        return len(self._connections)

    def get_metrics(self) -> dict:
        """
        Get comprehensive WebSocket metrics.

        Returns:
            Dictionary with connection and message metrics
        """
        metrics = ws_metrics.get_metrics()
        metrics.update({
            "current_connections": self.get_connection_count(),
            "current_users": self.get_user_count(),
            "subscribed_channels": len(self._channel_subscribers),
        })
        return metrics


# Singleton instance
manager = ConnectionManager()
