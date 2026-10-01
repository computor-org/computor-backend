"""Synthetic public Luna queue behavior against Redis-compatible Lua execution."""

import asyncio

import fakeredis.aioredis
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from computor_backend.api.public_luna import router
from computor_backend.redis_cache import get_redis_client
from computor_backend.services import public_luna_queue as queue


@pytest.fixture
def redis():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.mark.asyncio
async def test_one_pending_per_user_and_private_result(redis):
    first, job_id = await queue.admit(redis, "alice", {"question": "sentinel secret"})
    second, _ = await queue.admit(redis, "alice", {"question": "another"})
    assert (first, second) == ("accepted", "pending")
    assert await queue.status(redis, "bob", job_id) is None
    assert await queue.status(redis, "alice", job_id) == {"state": "queued"}

    claimed = await queue.claim(redis)
    assert claimed[0] == job_id
    assert claimed[2]["question"] == "sentinel secret"
    assert await queue.status(redis, "alice", job_id) == {"state": "running"}
    assert (
        await queue.finish(
            redis,
            job_id,
            claimed[1],
            {
                "state": "done",
                "answer": "synthetic answer",
                "user_id": "bob",
            },
        )
        == "finished"
    )
    assert await queue.status(redis, "bob", job_id) is None
    assert (await queue.status(redis, "alice", job_id))["answer"] == "synthetic answer"
    assert await redis.get(f"{queue.PREFIX}:job:{job_id}") is None
    assert (await queue.admit(redis, "alice", {"question": "next"}))[0] == "accepted"


@pytest.mark.asyncio
async def test_concurrent_admission_and_four_active(redis):
    outcomes = await asyncio.gather(
        *[queue.admit(redis, f"user-{i}", {"question": "synthetic"}) for i in range(30)]
    )
    assert sorted(status for status, _ in outcomes) == ["accepted"] * 20 + ["full"] * 10
    claims = await asyncio.gather(*[queue.claim(redis) for _ in range(12)])
    assert sum(item is not None for item in claims) == 4
    assert len({item[0] for item in claims if item}) == 4


@pytest.mark.asyncio
async def test_rolling_quota_and_stale_lease(redis, monkeypatch):
    now = 1_800_000_000
    monkeypatch.setattr(queue.time, "time", lambda: now)
    for index in range(10):
        outcome, job_id = await queue.admit(redis, "alice", {"question": str(index)})
        assert outcome == "accepted"
        claimed = await queue.claim(redis)
        assert (
            await queue.finish(
                redis,
                job_id,
                claimed[1],
                {
                    "state": "done",
                    "answer": "ok",
                },
            )
            == "finished"
        )
    assert (await queue.admit(redis, "alice", {"question": "eleventh"}))[0] == "quota"

    monkeypatch.setattr(queue.time, "time", lambda: now + 3601)
    outcome, job_id = await queue.admit(redis, "alice", {"question": "after hour"})
    assert outcome == "accepted"
    first = await queue.claim(redis)
    monkeypatch.setattr(queue.time, "time", lambda: now + 3601 + 601)
    assert (
        await queue.finish(redis, job_id, first[1], {"state": "done", "answer": "late"})
        == "stale"
    )
    second = await queue.claim(redis)
    assert second[0] == job_id and second[1] != first[1]
    assert (
        await queue.finish(redis, job_id, first[1], {"state": "done", "answer": "late"})
        == "stale"
    )
    assert (
        await queue.finish(
            redis, job_id, second[1], {"state": "done", "answer": "current"}
        )
        == "finished"
    )


@pytest.mark.asyncio
async def test_expired_job_cannot_be_completed(redis, monkeypatch):
    monkeypatch.setattr(queue.time, "time", lambda: 1_800_000_000)
    _, job_id = await queue.admit(redis, "alice", {"question": "synthetic"})
    claim = await queue.claim(redis)
    await redis.delete(f"{queue.PREFIX}:job:{job_id}")
    assert (
        await queue.finish(redis, job_id, claim[1], {"state": "done", "answer": "late"})
        == "expired"
    )
    assert await queue.status(redis, "alice", job_id) is None


def test_worker_http_route_requires_dedicated_secret(monkeypatch):
    monkeypatch.setenv("PUBLIC_LUNA_WORKER_KEY", "k" * 32)
    monkeypatch.setenv("PUBLIC_LUNA_ENABLED", "true")
    app = FastAPI()
    app.include_router(router)
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    app.dependency_overrides[get_redis_client] = lambda: fake
    client = TestClient(app)
    assert client.post("/worker/claim").status_code == 401
    assert (
        client.post("/worker/claim", headers={"X-API-Token": "k" * 32}).status_code
        == 401
    )
    response = client.post(
        "/worker/claim", headers={"X-Public-Luna-Worker-Key": "k" * 32}
    )
    assert response.status_code == 200
    assert response.json() == {"state": "idle"}
    monkeypatch.delenv("PUBLIC_LUNA_ENABLED")
    assert client.get("/availability").json() == {"enabled": False}
