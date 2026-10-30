"""Queue of Lena unit-description drafts (computor-org/issues#559).

The same atomic Redis queue as public Lena, under its own keys and limits: one
pending draft per lecturer, a small hourly and daily quota, results kept for an
hour. The worker's claims also mark it as alive, so the feature is offered only
while a Lena worker that knows this job type is polling or writing a draft.
"""

import json
import time

from computor_backend.services import public_luna_queue as _queue

PREFIX = "description_draft:v1"
MAX_PENDING = 20
PER_HOUR = 20
PER_DAY = 60
MAX_ACTIVE = 2
RESULT_TTL = 3600
# The worker polls every few seconds; a minute and a half without a claim
# means it is gone.
WORKER_SEEN_TTL = 90


async def admit(redis, user_id: str, payload: dict) -> tuple[str, str]:
    return await _queue.admit(
        redis, user_id, payload,
        prefix=PREFIX, max_pending=MAX_PENDING, per_hour=PER_HOUR, per_day=PER_DAY,
    )


async def claim(redis) -> tuple[str, str, dict] | None:
    await redis.set(f"{PREFIX}:worker", int(time.time()), ex=WORKER_SEEN_TTL)
    return await _queue.claim(redis, prefix=PREFIX, max_active=MAX_ACTIVE)


async def finish(redis, job_id: str, lease: str, result: dict) -> str:
    return await _queue.finish(
        redis, job_id, lease, result, prefix=PREFIX, result_ttl=RESULT_TTL
    )


async def requested(redis, job_id: str) -> dict | None:
    """The stored job payload, while the job is pending or running."""
    body = await redis.get(f"{PREFIX}:job:{job_id}")
    return json.loads(body) if body else None


async def status(redis, user_id: str, job_id: str) -> dict | None:
    return await _queue.status(redis, user_id, job_id, prefix=PREFIX)


async def cancel(redis, user_id: str, job_id: str) -> str:
    return await _queue.cancel(redis, user_id, job_id, prefix=PREFIX)


async def worker_alive(redis) -> bool:
    if await redis.exists(f"{PREFIX}:worker"):
        return True
    # A worker writing a long draft does not claim; its unexpired lease shows
    # it is still there.
    return await redis.zcount(f"{PREFIX}:active", int(time.time()), "+inf") > 0
