"""
Redis Pub/Sub abstraction for WebSocket broadcasting.

Provides multi-instance support by using Redis as a message broker.
When an event needs to be broadcast to subscribers, it's published to Redis,
and all backend instances receive it and forward to their local connections.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Callable, Awaitable, Optional, Set, Any

from computor_backend.redis_cache import get_redis_client
from computor_backend.settings import settings

logger = logging.getLogger(__name__)

# Pub/Sub channel prefixes
CHANNEL_PREFIX = "ws:broadcast:"
TYPING_PREFIX = "ws:typing:"


@dataclass
class RawPubSubMessage:
    """Raw message received from Redis pub/sub."""
    channel: str  # Full channel name with prefix
    data: bytes | str  # Raw message data
    message_type: str  # Redis message type (e.g., "message", "subscribe")


@dataclass
class ParsedPubSubMessage:
    """Parsed and validated pub/sub message ready for handling."""
    channel: str  # Logical channel name (prefix removed)
    data: dict  # Parsed JSON data


def parse_pubsub_message(raw: RawPubSubMessage) -> Optional[ParsedPubSubMessage]:
    """
    Parse and validate a raw pub/sub message.

    This function handles:
    - Filtering non-message types
    - Decoding bytes to strings
    - Removing channel prefix
    - Parsing JSON data

    Args:
        raw: Raw message from Redis pub/sub

    Returns:
        ParsedPubSubMessage if valid, None if should be skipped
    """
    # Only process actual messages (not subscribe/unsubscribe confirmations)
    if raw.message_type != "message":
        return None

    # Decode channel if bytes
    channel = raw.channel
    if isinstance(channel, bytes):
        channel = channel.decode("utf-8")

    # Remove prefix to get logical channel name
    if channel.startswith(CHANNEL_PREFIX):
        channel = channel[len(CHANNEL_PREFIX):]

    # Decode and parse data
    data = raw.data
    if isinstance(data, bytes):
        data = data.decode("utf-8")

    try:
        parsed_data = json.loads(data)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in pubsub message: {e}")
        return None

    return ParsedPubSubMessage(channel=channel, data=parsed_data)


class RedisPubSub:
    """
    Redis Pub/Sub manager for WebSocket event distribution.

    Supports multiple message handlers that are called for each received message.
    Handlers can be registered/unregistered dynamically.

    Example:
        async def my_handler(channel: str, data: dict):
            if data.get("type") == "message:new":
                # Handle new messages
                pass

        pubsub.register_handler("messaging", my_handler)
    """

    def __init__(self):
        self._pubsub = None
        self._listener_task: Optional[asyncio.Task] = None
        self._subscribed_channels: Set[str] = set()
        self._handlers: dict[str, Callable[[str, dict], Awaitable[None]]] = {}
        self._running = False

    def register_handler(self, name: str, handler: Callable[[str, dict], Awaitable[None]]):
        """
        Register a message handler.

        Args:
            name: Unique name for this handler (for logging/debugging)
            handler: Async callback called with (channel: str, data: dict)
        """
        self._handlers[name] = handler
        logger.info(f"Registered pubsub handler: {name}")

    def unregister_handler(self, name: str):
        """
        Unregister a message handler.

        Args:
            name: Name of the handler to remove
        """
        if name in self._handlers:
            del self._handlers[name]
            logger.info(f"Unregistered pubsub handler: {name}")

    async def start(self):
        """Start the pub/sub listener."""
        if self._running:
            logger.warning("PubSub listener already running")
            return

        redis_client = await get_redis_client()
        self._pubsub = redis_client.pubsub()
        self._running = True

        # Start listener task
        self._listener_task = asyncio.create_task(self._listen())
        logger.info(f"Redis PubSub listener started with {len(self._handlers)} handler(s)")

    async def stop(self):
        """Stop the pub/sub listener and clean up."""
        logger.info("Stopping Redis PubSub listener...")
        self._running = False

        if self._listener_task:
            self._listener_task.cancel()
            try:
                # Wait for task to finish with timeout
                await asyncio.wait_for(self._listener_task, timeout=2.0)
            except asyncio.CancelledError:
                pass
            except asyncio.TimeoutError:
                logger.warning("PubSub listener task did not stop within timeout")
            except Exception as e:
                logger.warning(f"Error stopping PubSub listener task: {e}")
            self._listener_task = None

        if self._pubsub:
            try:
                await asyncio.wait_for(self._pubsub.unsubscribe(), timeout=1.0)
            except asyncio.TimeoutError:
                logger.warning("PubSub unsubscribe timed out")
            except Exception as e:
                logger.warning(f"Error unsubscribing from PubSub: {e}")
            try:
                await asyncio.wait_for(self._pubsub.close(), timeout=1.0)
            except asyncio.TimeoutError:
                logger.warning("PubSub close timed out")
            except Exception as e:
                logger.warning(f"Error closing PubSub: {e}")
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
        """
        Background task that listens for pub/sub messages.

        Uses polling with timeout to allow graceful shutdown.
        The short timeout ensures we can check _running flag frequently.
        """
        logger.info("PubSub listener loop started")
        consecutive_errors = 0
        max_consecutive_errors = 10

        try:
            while self._running and self._pubsub:
                try:
                    # Wait until we have at least one subscription
                    if not self._subscribed_channels:
                        await asyncio.sleep(0.1)
                        continue

                    # Use get_message with timeout instead of listen()
                    # This allows us to check _running flag and respond to shutdown
                    raw_message = await self._pubsub.get_message(
                        ignore_subscribe_messages=True,
                        timeout=0.5  # Short timeout for responsive shutdown
                    )

                    if raw_message is None:
                        # No message received within timeout, just loop
                        continue

                    # Process the message
                    if raw_message.get("type") == "message":
                        await self._process_raw_message(raw_message)

                    # Reset error counter on successful iteration
                    consecutive_errors = 0

                except asyncio.CancelledError:
                    logger.info("PubSub listener received cancellation signal")
                    break
                except Exception as e:
                    consecutive_errors += 1
                    logger.error(f"PubSub listener error ({consecutive_errors}/{max_consecutive_errors}): {e}")

                    if consecutive_errors >= max_consecutive_errors:
                        logger.critical(f"PubSub listener exceeded max errors, stopping")
                        break

                    # Exponential backoff: 0.1s, 0.2s, 0.4s, ..., max 5s
                    backoff = min(0.1 * (2 ** (consecutive_errors - 1)), 5.0)
                    await asyncio.sleep(backoff)

        except asyncio.CancelledError:
            logger.info("PubSub listener cancelled")
        finally:
            logger.info("PubSub listener loop ended")

    async def _run_handler_with_timeout(
        self,
        handler_name: str,
        handler: Callable[[str, dict], Awaitable[None]],
        channel: str,
        data: dict
    ) -> bool:
        """
        Run a handler with timeout protection.

        Args:
            handler_name: Name of the handler for logging
            handler: The handler coroutine
            channel: Channel name
            data: Message data

        Returns:
            True if handler completed successfully, False otherwise
        """
        try:
            await asyncio.wait_for(
                handler(channel, data),
                timeout=settings.WS_HANDLER_TIMEOUT
            )
            return True
        except asyncio.TimeoutError:
            logger.warning(f"Handler '{handler_name}' timed out after {settings.WS_HANDLER_TIMEOUT}s on channel {channel}")
            return False
        except Exception as e:
            logger.error(f"Error in pubsub handler '{handler_name}': {e}")
            return False

    async def _process_raw_message(self, raw_message: dict):
        """
        Process a raw message from Redis pub/sub.

        This method converts the raw Redis message to our dataclass,
        parses it, and dispatches to all registered handlers concurrently
        with timeout protection.

        Args:
            raw_message: Raw message dict from Redis pub/sub
        """
        # Convert to our dataclass for type safety
        raw = RawPubSubMessage(
            channel=raw_message.get("channel", ""),
            data=raw_message.get("data", ""),
            message_type=raw_message.get("type", "")
        )

        # Parse and validate
        parsed = parse_pubsub_message(raw)
        if parsed is None:
            return  # Skip invalid or non-message types

        # Dispatch to all registered handlers concurrently with timeout protection
        handler_tasks = [
            self._run_handler_with_timeout(handler_name, handler, parsed.channel, parsed.data)
            for handler_name, handler in self._handlers.items()
        ]

        if handler_tasks:
            await asyncio.gather(*handler_tasks, return_exceptions=True)


class TypingTracker:
    """
    Track typing status using Redis with TTL.

    Typing indicators are stored as Redis keys with automatic expiry.
    This handles the case where a user closes the browser without
    explicitly stopping typing.
    """

    @property
    def typing_ttl(self) -> int:
        """Get typing TTL from settings."""
        return settings.WS_TYPING_TTL

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
        await redis_client.setex(key, self.typing_ttl, value)

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
