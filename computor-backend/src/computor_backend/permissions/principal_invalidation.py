"""Per-user principal invalidation (#384).

The Principal cache is keyed by ``sha256(kind:raw_token)`` (permissions/auth.py),
so when someone ELSE changes a user's permissions — a lecturer promoting a
student, an admin granting a role — the server cannot delete the affected
entries: it never sees the target's raw token. Before this module the stale
Principal kept answering for up to ``AUTH_CACHE_TTL`` (15 min) and only a
sign-out/sign-in (new token, new key) picked the change up.

``invalidate_user_principals`` is the one entry point. Per affected user it
1. stamps ``principal:stale:<user_id>`` with the current epoch time — the
   principal cache-HIT path compares this against ``Principal.built_at`` and
   rebuilds from the DB when the stamp is newer;
2. drops the 10-minute course-membership permission cache
   (``permissions/cache.py``), which backs most permission query filters;
3. publishes a ``permissions:updated`` event to the user's personal websocket
   inbox channel (``user:<id>``, auto-subscribed on connect) so connected
   clients can re-fetch their scopes instead of polling.

It is deliberately synchronous (safe with or without a running event loop) and
best-effort: cache invalidation must never fail the write that triggered it.
The main caller is the session ``after_commit`` hook in ``database.py``, which
fires whenever an ORM flush touched one of the membership tables — covering
CrudRouter, invites, imports and Temporal activities alike. Bulk
``query(...).update()`` writes bypass ORM flush events and must call this
directly (see ``business_logic/user_connect.py``).
"""

import json
import logging
import time
from typing import Iterable

logger = logging.getLogger(__name__)


def invalidate_user_principals(user_ids: Iterable[str]) -> None:
    """Mark every cached Principal of the given users stale and notify them."""
    ids = sorted({str(uid) for uid in user_ids if uid})
    if not ids:
        return

    from computor_backend.permissions.auth import (
        PRINCIPAL_STALE_TTL,
        principal_stale_key,
    )
    from computor_backend.permissions.cache import (
        invalidate_user_course_memberships_sync,
    )
    from computor_backend.redis_cache import get_sync_redis_client
    from computor_backend.websocket.pubsub import CHANNEL_PREFIX

    try:
        redis_client = get_sync_redis_client()
    except Exception:
        logger.warning("Principal invalidation skipped: no Redis client", exc_info=True)
        return

    now = time.time()
    for uid in ids:
        try:
            redis_client.set(principal_stale_key(uid), now, ex=PRINCIPAL_STALE_TTL)
            invalidate_user_course_memberships_sync(uid)
            channel = f"user:{uid}"
            redis_client.publish(
                f"{CHANNEL_PREFIX}{channel}",
                json.dumps({
                    "type": "permissions:updated",
                    "channel": channel,
                    "data": {"user_id": uid},
                }),
            )
            logger.info(f"Invalidated principals for user {uid} after permissions change")
        except Exception:
            logger.warning("Principal invalidation failed for user %s", uid, exc_info=True)
