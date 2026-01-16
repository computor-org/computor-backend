"""
Redis Pub/Sub abstraction for WebSocket broadcasting.

Provides multi-instance support by using Redis as a message broker.
When an event needs to be broadcast to subscribers, it's published to Redis,
and all backend instances receive it and forward to their local connections.
"""

import asyncio
import json
import logging
from typing import Callable, Awaitable, Optional, Set

from computor_backend.redis_cache import get_redis_client

logger = logging.getLogger(__name__)

# Pub/Sub channel prefixes
CHANNEL_PREFIX = "ws:broadcast:"
TYPING_PREFIX = "ws:typing:"


class RedisPubSub:
    """
    Redis Pub/Sub manager for WebSocket event distribution.

    Handles:
    - Subscribing to channels
    - Publishing events to channels
    - Managing pubsub listener task
    """

    def __init__(self):
        self._pubsub = None
        self._listener_task: Optional[asyncio.Task] = None
        self._subscribed_channels: Set[str] = set()
        self._message_handler: Optional[Callable[[str, dict], Awaitable[None]]] = None
        self._running = False

    async def start(self, message_handler: Callable[[str, dict], Awaitable[None]]):
        """
        Start the pub/sub listener.

        Args:
            message_handler: Async callback for handling received messages.
                            Called with (channel: str, data: dict)
        """
        if self._running:
            logger.warning("PubSub listener already running")
            return

        self._message_handler = message_handler
        redis_client = await get_redis_client()
        self._pubsub = redis_client.pubsub()
        self._running = True

        # Start listener task
        self._listener_task = asyncio.create_task(self._listen())
        logger.info("Redis PubSub listener started")

    async def stop(self):
        """Stop the pub/sub listener and clean up."""
        self._running = False

        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None

        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()
            self._pubsub = None

        self._subscribed_channels.clear()
        logger.info("Redis PubSub listener stopped")

    async def subscribe(self, channel: str):
        """
        Subscribe to a Redis pub/sub channel.

        Args:
            channel: Channel name (will be prefixed with CHANNEL_PREFIX)
        """
        if not self._pubsub:
            logger.warning("PubSub not initialized, cannot subscribe")
            return

        full_channel = f"{CHANNEL_PREFIX}{channel}"
        if full_channel not in self._subscribed_channels:
            await self._pubsub.subscribe(full_channel)
            self._subscribed_channels.add(full_channel)
            logger.debug(f"Subscribed to Redis channel: {full_channel}")

    async def unsubscribe(self, channel: str):
        """
        Unsubscribe from a Redis pub/sub channel.

        Args:
            channel: Channel name (will be prefixed with CHANNEL_PREFIX)
        """
        if not self._pubsub:
            return

        full_channel = f"{CHANNEL_PREFIX}{channel}"
        if full_channel in self._subscribed_channels:
            await self._pubsub.unsubscribe(full_channel)
            self._subscribed_channels.discard(full_channel)
            logger.debug(f"Unsubscribed from Redis channel: {full_channel}")

    async def publish(self, channel: str, event_type: str, data: dict):
        """
        Publish an event to a channel.

        Args:
            channel: Channel name (e.g., "submission_group:123")
            event_type: Event type (e.g., "message:new")
            data: Event data payload
        """
        redis_client = await get_redis_client()
        full_channel = f"{CHANNEL_PREFIX}{channel}"

        message = json.dumps({
            "type": event_type,
            "channel": channel,
            "data": data
        })

        await redis_client.publish(full_channel, message)
        logger.debug(f"Published to {full_channel}: {event_type}")

    async def _listen(self):
        """Background task that listens for pub/sub messages."""
        logger.info("PubSub listener loop started")

        try:
            while self._running and self._pubsub:
                try:
                    message = await self._pubsub.get_message(
                        ignore_subscribe_messages=True,
                        timeout=1.0
                    )

                    if message and message["type"] == "message":
                        channel = message["channel"]
                        if isinstance(channel, bytes):
                            channel = channel.decode("utf-8")

                        # Remove prefix to get the logical channel name
                        if channel.startswith(CHANNEL_PREFIX):
                            channel = channel[len(CHANNEL_PREFIX):]

                        try:
                            data = json.loads(message["data"])
                            if self._message_handler:
                                await self._message_handler(channel, data)
                        except json.JSONDecodeError as e:
                            logger.error(f"Invalid JSON in pubsub message: {e}")
                        except Exception as e:
                            logger.error(f"Error handling pubsub message: {e}")

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"PubSub listener error: {e}")
                    await asyncio.sleep(1)  # Brief pause before retry

        except asyncio.CancelledError:
            pass
        finally:
            logger.info("PubSub listener loop ended")


class TypingTracker:
    """
    Track typing status using Redis with TTL.

    Typing indicators are stored as Redis keys with automatic expiry.
    This handles the case where a user closes the browser without
    explicitly stopping typing.
    """

    TYPING_TTL = 5  # seconds

    async def set_typing(self, user_id: str, channel: str, user_name: Optional[str] = None):
        """
        Mark user as typing in a channel.

        Args:
            user_id: User ID
            channel: Channel (e.g., "submission_group:123")
            user_name: Optional user display name for broadcast
        """
        redis_client = await get_redis_client()

        # Store typing indicator with TTL
        key = f"{TYPING_PREFIX}{channel}:{user_id}"
        value = json.dumps({"user_name": user_name}) if user_name else "1"
        await redis_client.setex(key, self.TYPING_TTL, value)

        # Publish typing event
        await redis_client.publish(
            f"{TYPING_PREFIX}{channel}",
            json.dumps({
                "user_id": user_id,
                "user_name": user_name,
                "is_typing": True
            })
        )

        logger.debug(f"User {user_id} started typing in {channel}")

    async def stop_typing(self, user_id: str, channel: str):
        """
        Explicitly stop typing indicator.

        Args:
            user_id: User ID
            channel: Channel
        """
        redis_client = await get_redis_client()

        # Remove typing indicator
        key = f"{TYPING_PREFIX}{channel}:{user_id}"
        await redis_client.delete(key)

        # Publish stop typing event
        await redis_client.publish(
            f"{TYPING_PREFIX}{channel}",
            json.dumps({
                "user_id": user_id,
                "is_typing": False
            })
        )

        logger.debug(f"User {user_id} stopped typing in {channel}")

    async def get_typing_users(self, channel: str) -> list[dict]:
        """
        Get all users currently typing in a channel.

        Args:
            channel: Channel to check

        Returns:
            List of dicts with user_id and optional user_name
        """
        redis_client = await get_redis_client()
        pattern = f"{TYPING_PREFIX}{channel}:*"

        typing_users = []
        async for key in redis_client.scan_iter(match=pattern):
            # Extract user_id from key
            if isinstance(key, bytes):
                key = key.decode("utf-8")

            parts = key.split(":")
            if len(parts) >= 4:
                user_id = parts[-1]

                # Get user_name if stored
                value = await redis_client.get(key)
                user_name = None
                if value and value != "1":
                    try:
                        data = json.loads(value)
                        user_name = data.get("user_name")
                    except json.JSONDecodeError:
                        pass

                typing_users.append({
                    "user_id": user_id,
                    "user_name": user_name
                })

        return typing_users


# Singleton instances
pubsub = RedisPubSub()
typing_tracker = TypingTracker()
