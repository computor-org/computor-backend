"""Scheduling a one-shot self-update: validation, guards, and status round-trip."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import computor_backend.api.update as update_api
from computor_backend.api.update import (
    REDIS_KEY_AGENT,
    REDIS_KEY_REMOTE,
    REDIS_KEY_SCHEDULE,
    REDIS_KEY_SCHEDULE_RESULT,
    _build_status,
    cancel_scheduled_update,
    schedule_update,
)
from computor_backend.exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
)
from computor_backend.permissions.principal import Principal
from computor_types.update import SystemUpdateScheduleRequest


class FakeRedis:
    """Dict-backed stand-in for the async redis client (hashes + plain keys)."""

    def __init__(self):
        self.hashes: dict[str, dict] = {}
        self.keys: set[str] = set()

    async def exists(self, key):
        return key in self.keys or key in self.hashes

    async def hset(self, key, mapping=None):
        self.hashes.setdefault(key, {}).update(mapping or {})

    async def hgetall(self, key):
        return dict(self.hashes.get(key, {}))

    async def delete(self, *keys):
        for k in keys:
            self.hashes.pop(k, None)
            self.keys.discard(k)

    async def expire(self, key, ttl):
        pass


def _admin() -> Principal:
    return Principal(user_id="admin", roles=["_admin"])


def _db(given_name="Ada", family_name="Admin") -> MagicMock:
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = MagicMock(
        given_name=given_name, family_name=family_name
    )
    return db


def _settings(enabled=True):
    settings = MagicMock()
    settings.update.enabled = enabled
    settings.update.repo_branch = "main"
    settings.update.repo_url = "https://example.invalid/repo.git"
    settings.update.repo_token = None
    return settings


def _patched(redis, enabled=True):
    return (
        patch.object(update_api, "get_settings", return_value=_settings(enabled)),
        patch.object(update_api, "get_redis_client", AsyncMock(return_value=redis)),
    )


def _future(minutes=30) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


@pytest.mark.asyncio
async def test_schedule_requires_admin():
    with pytest.raises(ForbiddenException):
        await schedule_update(
            SystemUpdateScheduleRequest(scheduled_at=_future()),
            Principal(user_id="student", roles=[]),
            _db(),
        )


@pytest.mark.asyncio
async def test_schedule_rejected_when_update_disabled():
    redis = FakeRedis()
    p1, p2 = _patched(redis, enabled=False)
    with p1, p2, pytest.raises(BadRequestException):
        await schedule_update(
            SystemUpdateScheduleRequest(scheduled_at=_future()), _admin(), _db()
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("scheduled_at", ["not-a-date", "2020-01-01T00:00:00+00:00"])
async def test_schedule_rejects_garbage_and_past_datetimes(scheduled_at):
    redis = FakeRedis()
    redis.keys.add(REDIS_KEY_AGENT)
    p1, p2 = _patched(redis)
    with p1, p2, pytest.raises(BadRequestException):
        await schedule_update(
            SystemUpdateScheduleRequest(scheduled_at=scheduled_at), _admin(), _db()
        )


@pytest.mark.asyncio
async def test_schedule_rejected_without_updater_heartbeat():
    redis = FakeRedis()  # no update:agent key
    p1, p2 = _patched(redis)
    with p1, p2, pytest.raises(ConflictException):
        await schedule_update(
            SystemUpdateScheduleRequest(scheduled_at=_future()), _admin(), _db()
        )


@pytest.mark.asyncio
async def test_schedule_writes_iso_and_matching_epoch():
    redis = FakeRedis()
    redis.keys.add(REDIS_KEY_AGENT)
    scheduled_at = _future(minutes=90)
    p1, p2 = _patched(redis)
    with p1, p2:
        response = await schedule_update(
            SystemUpdateScheduleRequest(scheduled_at=scheduled_at), _admin(), _db()
        )

    stored = redis.hashes[REDIS_KEY_SCHEDULE]
    assert response.status == "scheduled"
    assert response.scheduled_by_name == "Ada Admin"
    assert stored["scheduled_by"] == "admin"
    parsed = datetime.fromisoformat(stored["scheduled_at"])
    assert int(stored["scheduled_at_epoch"]) == int(parsed.timestamp())
    assert parsed == datetime.fromisoformat(scheduled_at)


@pytest.mark.asyncio
async def test_schedule_naive_datetime_is_treated_as_utc():
    redis = FakeRedis()
    redis.keys.add(REDIS_KEY_AGENT)
    naive = (datetime.now(timezone.utc) + timedelta(hours=2)).replace(tzinfo=None)
    p1, p2 = _patched(redis)
    with p1, p2:
        await schedule_update(
            SystemUpdateScheduleRequest(scheduled_at=naive.isoformat()), _admin(), _db()
        )

    stored = redis.hashes[REDIS_KEY_SCHEDULE]
    assert datetime.fromisoformat(stored["scheduled_at"]) == naive.replace(
        tzinfo=timezone.utc
    )


@pytest.mark.asyncio
async def test_reschedule_replaces_existing_schedule():
    redis = FakeRedis()
    redis.keys.add(REDIS_KEY_AGENT)
    p1, p2 = _patched(redis)
    with p1, p2:
        await schedule_update(
            SystemUpdateScheduleRequest(scheduled_at=_future(minutes=30)), _admin(), _db()
        )
        first = dict(redis.hashes[REDIS_KEY_SCHEDULE])
        await schedule_update(
            SystemUpdateScheduleRequest(scheduled_at=_future(minutes=60)), _admin(), _db()
        )

    second = redis.hashes[REDIS_KEY_SCHEDULE]
    assert second["scheduled_at"] != first["scheduled_at"]
    assert int(second["scheduled_at_epoch"]) > int(first["scheduled_at_epoch"])


@pytest.mark.asyncio
async def test_cancel_schedule_is_idempotent():
    redis = FakeRedis()
    redis.hashes[REDIS_KEY_SCHEDULE] = {"scheduled_at": _future()}
    with patch.object(update_api, "get_redis_client", AsyncMock(return_value=redis)):
        assert (await cancel_scheduled_update(_admin()))["status"] == "cancelled"
        assert REDIS_KEY_SCHEDULE not in redis.hashes
        # Second cancel with nothing scheduled must not error.
        assert (await cancel_scheduled_update(_admin()))["status"] == "cancelled"


@pytest.mark.asyncio
async def test_cancel_schedule_requires_admin():
    with pytest.raises(ForbiddenException):
        await cancel_scheduled_update(Principal(user_id="student", roles=[]))


@pytest.mark.asyncio
async def test_status_round_trips_schedule_and_result(monkeypatch):
    redis = FakeRedis()
    # Pre-cached remote state so _build_status never shells out to git.
    redis.hashes[REDIS_KEY_REMOTE] = {
        "commit": "b" * 40,
        "checked_at": "2026-07-20T00:00:00+00:00",
        "error": "",
    }
    scheduled_at = _future()
    redis.hashes[REDIS_KEY_SCHEDULE] = {
        "scheduled_at": scheduled_at,
        "scheduled_at_epoch": "1",
        "scheduled_by": "admin",
        "scheduled_by_name": "Ada Admin",
        "created_at": "2026-07-20T00:00:00+00:00",
    }
    redis.hashes[REDIS_KEY_SCHEDULE_RESULT] = {
        "outcome": "missed",
        "scheduled_at": "2026-07-19T03:00:00+00:00",
        "resolved_at": "2026-07-19T05:00:00+00:00",
        "detail": "The system was unavailable at the scheduled time; the update was not run.",
    }
    monkeypatch.setattr(update_api, "_running_version", ("a" * 40, "main"))

    with patch.object(update_api, "get_settings", return_value=_settings()):
        status = await _build_status(redis)

    assert status.schedule is not None
    assert status.schedule.scheduled_at == scheduled_at
    assert status.schedule.scheduled_by_name == "Ada Admin"
    assert status.last_schedule_result is not None
    assert status.last_schedule_result.outcome == "missed"


@pytest.mark.asyncio
async def test_status_has_no_schedule_when_none_pending(monkeypatch):
    redis = FakeRedis()
    redis.hashes[REDIS_KEY_REMOTE] = {
        "commit": "b" * 40,
        "checked_at": "2026-07-20T00:00:00+00:00",
        "error": "",
    }
    monkeypatch.setattr(update_api, "_running_version", ("a" * 40, "main"))

    with patch.object(update_api, "get_settings", return_value=_settings()):
        status = await _build_status(redis)

    assert status.schedule is None
    assert status.last_schedule_result is None
