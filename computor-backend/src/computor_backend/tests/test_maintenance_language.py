"""Maintenance texts in German and English (each client shows its reader's language).

Built-in texts always travel as ``message_i18n`` beside the English ``message``;
an admin's own text stays one language unless the admin sends both.
DB-free: Redis and the WebSocket pub/sub are replaced by fakes.
"""
from types import SimpleNamespace

import pytest

from computor_backend import maintenance_scheduler
from computor_backend.api import maintenance
from computor_backend.websocket import pubsub as pubsub_module
from computor_types.maintenance import MaintenanceActivate, MaintenanceSchedule

ADMIN = SimpleNamespace(user_id="admin-1", is_admin=True)


class FakeRedis:
    def __init__(self):
        self.hashes = {}

    async def hset(self, key, mapping):
        self.hashes.setdefault(key, {}).update(mapping)

    async def hgetall(self, key):
        return dict(self.hashes.get(key, {}))

    async def delete(self, *keys):
        for key in keys:
            self.hashes.pop(key, None)


class FakeDb:
    def query(self, _model):
        return self

    def filter(self, *_args):
        return self

    def first(self):
        return None


@pytest.fixture
def env(monkeypatch):
    redis = FakeRedis()
    events = []

    async def _redis():
        return redis

    async def _publish(channel, event_type, data):
        events.append((event_type, data))

    monkeypatch.setattr(maintenance, "get_redis_client", _redis)
    monkeypatch.setattr(maintenance_scheduler, "get_redis_client", _redis)
    monkeypatch.setattr(pubsub_module, "pubsub", SimpleNamespace(publish=_publish))
    return SimpleNamespace(redis=redis, events=events)


@pytest.mark.asyncio
async def test_default_activation_text_comes_in_both_languages(env):
    await maintenance.activate_maintenance(MaintenanceActivate(), ADMIN, FakeDb())

    (event_type, data), = env.events
    assert event_type == "maintenance:activated"
    assert data["message"] == "The system is undergoing scheduled maintenance."
    assert data["message_i18n"] == {
        "de": "Das System wird gerade planmäßig gewartet.",
        "en": "The system is undergoing scheduled maintenance.",
    }
    status = await maintenance.get_maintenance_status(ADMIN)
    assert status.message_i18n == data["message_i18n"]


@pytest.mark.asyncio
async def test_admin_text_in_both_languages_reaches_status_and_event(env):
    pair = {"de": "Heute ab 18 Uhr gesperrt.", "en": "Locked from 6 pm today.", "fr": "ignored"}
    request = MaintenanceActivate(message="Locked from 6 pm today.", message_i18n=pair)
    await maintenance.activate_maintenance(request, ADMIN, FakeDb())

    expected = {"de": "Heute ab 18 Uhr gesperrt.", "en": "Locked from 6 pm today."}
    assert env.events[0][1]["message_i18n"] == expected
    status = await maintenance.get_maintenance_status(ADMIN)
    assert status.message == "Locked from 6 pm today."
    assert status.message_i18n == expected


@pytest.mark.asyncio
async def test_admin_text_in_one_language_has_no_pair(env):
    await maintenance.activate_maintenance(MaintenanceActivate(message="Kurz offline."), ADMIN, FakeDb())
    # A second activation must not inherit the first one's pair.
    assert "message_i18n" not in env.events[0][1]
    assert (await maintenance.get_maintenance_status(ADMIN)).message_i18n is None


@pytest.mark.asyncio
async def test_deactivate_and_cancel_texts_come_in_both_languages(env):
    await maintenance.deactivate_maintenance(ADMIN)
    await maintenance.cancel_scheduled_maintenance(ADMIN)

    by_type = dict(env.events)
    assert by_type["maintenance:deactivated"]["message_i18n"]["de"] == (
        "Die Wartung ist abgeschlossen. Alle Funktionen stehen wieder zur Verfügung."
    )
    assert by_type["maintenance:cancelled"]["message_i18n"] == {
        "de": "Die geplante Wartung wurde abgesagt.",
        "en": "Scheduled maintenance has been cancelled.",
    }


@pytest.mark.asyncio
async def test_reminder_keeps_the_scheduled_pair(env):
    await maintenance.schedule_maintenance(
        MaintenanceSchedule(scheduled_at="2999-01-01T00:00:00Z"), ADMIN, FakeDb()
    )
    stored = await env.redis.hgetall("maintenance:schedule")
    await maintenance_scheduler.MaintenanceReminderScheduler()._check_schedule(
        "maintenance:schedule", maintenance_scheduler.WATCHED_SCHEDULES[0][1],
        {**stored, "scheduled_at": _minutes_from_now(5)},
    )

    reminder = env.events[-1][1]
    assert reminder["minutes_remaining"] == 5
    assert reminder["message_i18n"] == {
        "de": "Eine Wartung ist geplant.",
        "en": "Scheduled maintenance is planned.",
    }


@pytest.mark.asyncio
async def test_update_reminder_without_message_uses_built_in_pair(env):
    await maintenance_scheduler.MaintenanceReminderScheduler()._check_schedule(
        "update:schedule", maintenance_scheduler.WATCHED_SCHEDULES[1][1],
        {"scheduled_at": _minutes_from_now(10)},
    )

    (_, reminder), = env.events
    assert reminder["message"] == "The system will restart for a scheduled update."
    assert reminder["message_i18n"]["de"] == "Das System startet für ein geplantes Update neu."


def _minutes_from_now(minutes: float) -> str:
    from datetime import datetime, timedelta, timezone

    # Half a minute inside the threshold window, so exactly one reminder fires.
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes - 0.5)).isoformat()
