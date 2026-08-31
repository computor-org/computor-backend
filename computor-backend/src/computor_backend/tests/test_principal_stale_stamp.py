"""A permissions change must reach affected users without a re-login (#384).

The Principal cache is keyed by the raw token, so changing SOMEONE ELSE's
permissions (course-member role update, user-role grant, org/family membership)
cannot delete the affected entries. The fix is a per-user stale stamp written on
commit and compared against ``Principal.built_at`` on the cache-HIT path, plus a
``permissions:updated`` websocket push on the user's personal inbox channel.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from computor_backend.database import (
    _PERMISSION_STALE_KEY,
    _drop_stale_principal_tracking,
    _invalidate_stale_principals,
    _track_permission_membership_writes,
)
from computor_backend.exceptions import ForbiddenException
from computor_backend.model.course import CourseFamilyMember, CourseMember
from computor_backend.model.organization import OrganizationMember
from computor_backend.model.role import UserRole
from computor_backend.permissions import principal_invalidation
from computor_backend.permissions.auth import (
    AUTH_CACHE_TTL,
    BANNED_FLAG_PREFIX,
    PRINCIPAL_STALE_TTL,
    _get_cached_principal,
    principal_stale_key,
)
from computor_backend.permissions.principal import Principal
from computor_backend.websocket.pubsub import CHANNEL_PREFIX


USER_ID = "11111111-1111-1111-1111-111111111111"
CACHE_KEY = "some-principal-cache-key"


class FakeRedis:
    """Minimal async Redis stand-in for the cache-hit path."""

    def __init__(self, values=None):
        self.values = dict(values or {})

    async def get(self, key):
        return self.values.get(key)

    async def mget(self, *keys):
        return [self.values.get(key) for key in keys]


class FakeSyncRedis:
    """Records set/publish calls made by invalidate_user_principals."""

    def __init__(self):
        self.sets = []
        self.published = []

    def set(self, key, value, ex=None):
        self.sets.append((key, value, ex))

    def publish(self, channel, message):
        self.published.append((channel, message))


def _cached(built_at):
    return Principal(user_id=USER_ID, roles=["user"], built_at=built_at).model_dump_json()


def _patched_redis(redis):
    return patch(
        "computor_backend.permissions.auth.get_redis_client",
        AsyncMock(return_value=redis),
    )


# ---------------------------------------------------------------------------
# Cache-hit path: the stale stamp decides whether the entry is served
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stamp_newer_than_snapshot_forces_a_rebuild():
    """The regression: a role change must not keep answering from cache."""
    redis = FakeRedis({
        CACHE_KEY: _cached(built_at=100.0),
        principal_stale_key(USER_ID): "200.0",
    })
    with _patched_redis(redis):
        assert await _get_cached_principal(CACHE_KEY) is None


@pytest.mark.asyncio
async def test_snapshot_built_after_the_stamp_is_served():
    redis = FakeRedis({
        CACHE_KEY: _cached(built_at=300.0),
        principal_stale_key(USER_ID): "200.0",
    })
    with _patched_redis(redis):
        principal = await _get_cached_principal(CACHE_KEY)
    assert principal is not None and principal.user_id == USER_ID


@pytest.mark.asyncio
async def test_no_stamp_serves_the_cache():
    redis = FakeRedis({CACHE_KEY: _cached(built_at=100.0)})
    with _patched_redis(redis):
        assert await _get_cached_principal(CACHE_KEY) is not None


@pytest.mark.asyncio
async def test_pre_upgrade_entry_without_built_at_counts_as_stale():
    entry = json.loads(_cached(built_at=None))
    entry.pop("built_at", None)
    redis = FakeRedis({
        CACHE_KEY: json.dumps(entry),
        principal_stale_key(USER_ID): "200.0",
    })
    with _patched_redis(redis):
        assert await _get_cached_principal(CACHE_KEY) is None


@pytest.mark.asyncio
async def test_ban_flag_still_enforced_on_the_shared_mget():
    redis = FakeRedis({
        CACHE_KEY: _cached(built_at=100.0),
        f"{BANNED_FLAG_PREFIX}{USER_ID}": "1",
    })
    with _patched_redis(redis):
        with pytest.raises(ForbiddenException):
            await _get_cached_principal(CACHE_KEY)


def test_stamp_outlives_the_principal_cache():
    """If AUTH_CACHE_TTL is ever raised past the stamp TTL, the window reopens."""
    assert PRINCIPAL_STALE_TTL >= AUTH_CACHE_TTL


# ---------------------------------------------------------------------------
# invalidate_user_principals: stamp + membership cache + websocket push
# ---------------------------------------------------------------------------


def test_invalidation_stamps_busts_membership_cache_and_publishes():
    redis = FakeSyncRedis()
    membership = MagicMock()
    with patch("computor_backend.redis_cache.get_sync_redis_client", return_value=redis), \
         patch("computor_backend.permissions.cache.invalidate_user_course_memberships_sync", membership):
        principal_invalidation.invalidate_user_principals([USER_ID, USER_ID, None])

    assert len(redis.sets) == 1
    key, value, ex = redis.sets[0]
    assert key == principal_stale_key(USER_ID)
    assert float(value) > 0
    assert ex == PRINCIPAL_STALE_TTL

    membership.assert_called_once_with(USER_ID)

    assert len(redis.published) == 1
    channel, message = redis.published[0]
    assert channel == f"{CHANNEL_PREFIX}user:{USER_ID}"
    event = json.loads(message)
    assert event["type"] == "permissions:updated"
    assert event["channel"] == f"user:{USER_ID}"


def test_invalidation_survives_a_redis_outage():
    with patch(
        "computor_backend.redis_cache.get_sync_redis_client",
        side_effect=RuntimeError("redis down"),
    ):
        principal_invalidation.invalidate_user_principals([USER_ID])  # must not raise


# ---------------------------------------------------------------------------
# Session listeners: membership writes are tracked per flush, acted on at commit
# ---------------------------------------------------------------------------


class FakeSession:
    def __init__(self, new=(), dirty=(), deleted=()):
        self.new = set(new)
        self.dirty = set(dirty)
        self.deleted = set(deleted)
        self.info = {}


def test_flush_listener_collects_user_ids_from_all_membership_tables():
    session = FakeSession(
        new=[UserRole(user_id="u-role"), object()],
        dirty=[CourseMember(user_id="u-course"), OrganizationMember(user_id="u-org")],
        deleted=[CourseFamilyMember(user_id="u-family")],
    )
    _track_permission_membership_writes(session, None)
    assert session.info[_PERMISSION_STALE_KEY] == {
        "u-role", "u-course", "u-org", "u-family",
    }


def test_flush_listener_ignores_unrelated_writes():
    session = FakeSession(new=[object()], dirty=[object()])
    _track_permission_membership_writes(session, None)
    assert _PERMISSION_STALE_KEY not in session.info


def test_commit_listener_invalidates_and_clears_the_tracking():
    session = FakeSession()
    session.info[_PERMISSION_STALE_KEY] = {"u1", "u2"}
    with patch(
        "computor_backend.permissions.principal_invalidation.invalidate_user_principals"
    ) as invalidate:
        _invalidate_stale_principals(session)
    invalidate.assert_called_once_with({"u1", "u2"})
    assert _PERMISSION_STALE_KEY not in session.info


def test_rollback_drops_the_tracking_without_invalidating():
    session = FakeSession()
    session.info[_PERMISSION_STALE_KEY] = {"u1"}
    with patch(
        "computor_backend.permissions.principal_invalidation.invalidate_user_principals"
    ) as invalidate:
        _drop_stale_principal_tracking(session)
    invalidate.assert_not_called()
    assert _PERMISSION_STALE_KEY not in session.info
