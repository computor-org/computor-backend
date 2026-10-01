"""Exercise Luna admission errors through the real ASGI exception stack."""

import json
from types import SimpleNamespace
from uuid import uuid4

import fakeredis.aioredis
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from redis.exceptions import RedisError

from computor_backend.api import public_luna
from computor_backend.database import get_db
from computor_backend.exceptions import register_exception_handlers
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.public_luna_privacy import PublicLunaPrivacyMiddleware
from computor_backend.redis_cache import get_redis_client
from computor_backend.services import public_luna_queue as queue

SENTINEL = "private-learner-text-do-not-log"
CONTENT_ID = str(uuid4())


@pytest.fixture
def luna_client(monkeypatch):
    monkeypatch.setenv("PUBLIC_LUNA_ENABLED", "true")
    monkeypatch.setenv("PUBLIC_LUNA_WORKER_KEY", "synthetic-worker-key-longer-than-32-characters")
    monkeypatch.setattr(
        public_luna, "_visible_assignment",
        lambda _db, _user, _content: SimpleNamespace(
            title="Synthetic assignment", description="A short task", deployment=None
        ),
    )
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    actor = {"user_id": "owned-learner"}
    app = FastAPI(root_path="/api")
    app.include_router(public_luna.router, prefix="/public-luna")
    register_exception_handlers(app)
    app.add_middleware(PublicLunaPrivacyMiddleware)
    app.dependency_overrides[get_current_principal] = lambda: Principal(user_id=actor["user_id"])
    app.dependency_overrides[get_db] = lambda: None
    app.dependency_overrides[get_redis_client] = lambda: redis
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client, actor


def payload(**overrides):
    return {
        "course_content_id": CONTENT_ID,
        "question": SENTINEL,
        "submitted_text": SENTINEL,
        **overrides,
    }


def assert_private(caplog, response):
    assert SENTINEL not in response.text
    assert SENTINEL not in caplog.text
    assert SENTINEL not in json.dumps([record.__dict__ for record in caplog.records], default=str)
    assert all(record.exc_info is None for record in caplog.records)


@pytest.mark.parametrize("outcome,expected", [
    ("pending", "A Luna request is already pending"),
    ("full", "Luna is busy; try again later"),
    ("quota", "Luna request limit reached"),
])
def test_admission_returns_429_without_logging_text(luna_client, monkeypatch, caplog, outcome, expected):
    async def reject(_redis, _user_id, _body):
        return outcome, str(uuid4())

    monkeypatch.setattr(queue, "admit", reject)
    response = luna_client[0].post("/public-luna/requests", json=payload())
    assert response.status_code == 429
    assert response.json() == {"message": expected}
    assert_private(caplog, response)


def test_redis_outage_returns_503_without_logging_text(luna_client, monkeypatch, caplog):
    async def fail(_redis, _user_id, _body):
        raise RedisError(SENTINEL)

    monkeypatch.setattr(queue, "admit", fail)
    response = luna_client[0].post("/public-luna/requests", json=payload())
    assert response.status_code == 503
    assert_private(caplog, response)


def test_oversized_request_returns_413_without_logging_text(luna_client, monkeypatch, caplog):
    monkeypatch.setattr(
        public_luna, "_visible_assignment",
        lambda _db, _user, _content: SimpleNamespace(
            title="Synthetic", description="x" * 5000, deployment=None
        ),
    )
    response = luna_client[0].post(
        "/public-luna/requests",
        json=payload(question=SENTINEL + "q" * (6000 - len(SENTINEL)), submitted_text="s" * 16000),
    )
    assert response.status_code == 413
    assert response.json() == {"message": "Luna request is too large"}
    assert_private(caplog, response)


def test_other_authenticated_user_cannot_read_queued_job(luna_client, caplog):
    client, actor = luna_client
    submitted = client.post("/public-luna/requests", json=payload())
    assert submitted.status_code == 202
    job_id = submitted.json()["id"]
    actor["user_id"] = "another-owned-learner"
    denied = client.get(f"/public-luna/requests/{job_id}")
    assert denied.status_code == 404
    assert_private(caplog, denied)
    actor["user_id"] = "owned-learner"
    allowed = client.get(f"/public-luna/requests/{job_id}")
    assert allowed.status_code == 200
    assert allowed.json() == {"state": "queued"}
