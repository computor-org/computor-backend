"""
Background scheduler that broadcasts maintenance countdown reminders.

Polls Redis for scheduled maintenance and broadcasts `maintenance:reminder`
events at predefined thresholds (30, 20, 10, 5, 4, 3, 2, 1 minutes before).
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from computor_backend.redis_cache import get_redis_client

logger = logging.getLogger(__name__)

REDIS_KEY_SCHEDULE = "maintenance:schedule"
POLL_INTERVAL_SECONDS = 30
REMINDER_THRESHOLDS = [30, 20, 10, 5, 4, 3, 2, 1]


class MaintenanceReminderScheduler:
    """Periodically checks for scheduled maintenance and broadcasts countdown reminders."""

    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._sent_thresholds: set[int] = set()
        self._current_scheduled_at: Optional[str] = None

    async def start(self):
        """Start the background reminder loop."""
        if self._running:
            logger.warning("Maintenance reminder scheduler already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Maintenance reminder scheduler started")

    async def stop(self):
        """Stop the background reminder loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Maintenance reminder scheduler stopped")

    async def _loop(self):
        """Main polling loop."""
        try:
            while self._running:
                try:
                    await self._check_and_broadcast()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Maintenance reminder check failed: {e}")

                await asyncio.sleep(POLL_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            logger.info("Maintenance reminder loop cancelled")

    async def _check_and_broadcast(self):
        """Check schedule in Redis and broadcast reminders at thresholds."""
        redis = await get_redis_client()
        schedule = await redis.hgetall(REDIS_KEY_SCHEDULE)

        if not schedule or not schedule.get("scheduled_at"):
            # No schedule — reset tracking
            if self._current_scheduled_at is not None:
                self._current_scheduled_at = None
                self._sent_thresholds.clear()
            return

        scheduled_at_str = schedule["scheduled_at"]
        message = schedule.get("message", "Scheduled maintenance is approaching.")

        # Detect schedule change — reset thresholds
        if scheduled_at_str != self._current_scheduled_at:
            logger.info(f"Maintenance schedule detected/changed: {scheduled_at_str}")
            self._current_scheduled_at = scheduled_at_str
            self._sent_thresholds.clear()

        # Parse scheduled time
        try:
            raw = scheduled_at_str.replace("Z", "+00:00")
            scheduled_dt = datetime.fromisoformat(raw)
            if scheduled_dt.tzinfo is None:
                scheduled_dt = scheduled_dt.replace(tzinfo=timezone.utc)
        except ValueError:
            logger.warning(f"Invalid scheduled_at in Redis: {scheduled_at_str}")
            return

        now = datetime.now(timezone.utc)
        minutes_remaining = (scheduled_dt - now).total_seconds() / 60

        if minutes_remaining <= 0:
            # Past the scheduled time — no more reminders
            return

        for threshold in REMINDER_THRESHOLDS:
            if threshold in self._sent_thresholds:
                continue

            if minutes_remaining <= threshold:
                if minutes_remaining < threshold - 1.5:
                    # This threshold is well past — mark sent without broadcasting
                    # (avoids sending "30 min reminder" when only 3 min remain)
                    self._sent_thresholds.add(threshold)
                else:
                    # Within the threshold window — broadcast
                    await self._broadcast_reminder(threshold, scheduled_at_str, message)
                    self._sent_thresholds.add(threshold)

    async def _broadcast_reminder(self, minutes_remaining: int, scheduled_at: str, message: str):
        """Broadcast a maintenance:reminder event via Redis pub/sub."""
        logger.info(f"Broadcasting maintenance reminder: {minutes_remaining} min remaining")
        try:
            from computor_backend.websocket.pubsub import pubsub

            await pubsub.publish("system:maintenance", "maintenance:reminder", {
                "minutes_remaining": minutes_remaining,
                "scheduled_at": scheduled_at,
                "message": message,
            })
        except Exception as e:
            logger.error(f"Failed to broadcast maintenance reminder: {e}")
