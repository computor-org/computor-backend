"""Background reconciliation of test ``Result`` rows against Temporal.

A ``Result`` row is created QUEUED before the workflow starts, and the worker
is what later PATCHes it to its terminal state. If the worker dies between
those two points — SIGKILL, OOM, a lost API call, an expired token — nothing
in the request path notices: ``sync_result_status_from_temporal`` only ever ran
from ``POST /tests`` and ``GET /tests/status/{id}``. A student who submits and
closes the tab therefore left a row QUEUED forever, and because the in-progress
statuses take part in the partial unique indexes on ``result``, that ghost row
also blocked every later test of the same version.

This scheduler closes the loop: periodically re-ask Temporal about rows that
have been in progress for longer than any healthy run should be, and write the
real outcome. It is deliberately conservative — it only touches rows older than
``RECONCILE_MIN_AGE_MINUTES`` so it never races the live polling path.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from computor_backend.business_logic.testing_orchestration import (
    IN_PROGRESS_STATUSES,
    sync_result_status_from_temporal,
)
from computor_backend.database import get_db_session
from computor_backend.model.result import Result
from computor_backend.redis_cache import get_redis_client

logger = logging.getLogger(__name__)

# How often to sweep.
POLL_INTERVAL_SECONDS = 300

# Only reconcile rows that have been in progress at least this long. The
# student-testing workflow has a 30 minute execution timeout, so anything
# older than this is either finished-but-unreported or genuinely gone; either
# way the live polling path has had ample opportunity to handle it first.
RECONCILE_MIN_AGE_MINUTES = 35

# Cap the work per sweep so a backlog can never monopolise the event loop or
# stampede Temporal. Leftovers are picked up by the next sweep.
RECONCILE_BATCH_SIZE = 100

# Only one API replica should sweep at a time.
LOCK_KEY = "testing:result_reconciler:lock"
LOCK_TTL_SECONDS = POLL_INTERVAL_SECONDS - 30


async def _acquire_lock() -> bool:
    """Best-effort cross-replica mutex. Fails open to *not* running."""
    try:
        redis = await get_redis_client()
        return bool(await redis.set(LOCK_KEY, "1", ex=LOCK_TTL_SECONDS, nx=True))
    except Exception as e:  # pragma: no cover - redis hiccup
        logger.warning(f"Result reconciler could not acquire lock: {e}")
        return False


def _find_stale_results(db, cutoff: datetime) -> list[Result]:
    return (
        db.query(Result)
        .filter(
            Result.status.in_(IN_PROGRESS_STATUSES),
            Result.created_at < cutoff,
        )
        .order_by(Result.created_at.asc())
        .limit(RECONCILE_BATCH_SIZE)
        .all()
    )


async def reconcile_stale_results() -> int:
    """Reconcile one batch of stale in-progress results. Returns rows changed."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=RECONCILE_MIN_AGE_MINUTES)
    changed = 0

    with get_db_session() as db:
        stale = _find_stale_results(db, cutoff)
        if not stale:
            return 0

        logger.info("Result reconciler: checking %d stale in-progress result(s)", len(stale))
        for result in stale:
            before = result.status
            try:
                # treat_missing_as_crashed: a workflow Temporal no longer knows
                # about is never coming back, so the row must not stay QUEUED.
                # sync_in_progress: also persist RUNNING, so a long but healthy
                # run is left alone rather than repeatedly re-examined.
                await sync_result_status_from_temporal(
                    result, db, treat_missing_as_crashed=True, sync_in_progress=True
                )
            except Exception as e:
                logger.warning("Could not reconcile Result %s: %s", result.id, e)
                continue

            if result.status != before:
                changed += 1
                logger.info(
                    "Result reconciler: Result %s %s -> %s", result.id, before, result.status
                )

    return changed


class ResultReconciler:
    """Periodically reconciles stale in-progress ``Result`` rows."""

    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        if self._running:
            logger.warning("Result reconciler already running")
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Result reconciler started")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Result reconciler stopped")

    async def _loop(self):
        try:
            while self._running:
                # Sleep first: at boot the workers may not have reconnected yet,
                # and nothing here is urgent.
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
                if not self._running:
                    break
                try:
                    if await _acquire_lock():
                        await reconcile_stale_results()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Result reconciliation sweep failed: {e}")
        except asyncio.CancelledError:
            logger.info("Result reconciler loop cancelled")
