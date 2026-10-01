"""Public Luna visibility and ownership against the real PostgreSQL schema."""

import os
import uuid

import fakeredis.aioredis
import pytest
from fastapi import FastAPI, HTTPException, Response
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import Ltree

from computor_backend.api.public_luna import (
    LunaRequest,
    _visible_assignment,
    router,
    submit_request,
)
from computor_backend.database import get_db
from computor_backend.model.auth import User
from computor_backend.model.course import (
    Course,
    CourseContent,
    CourseContentKind,
    CourseContentType,
    CourseFamily,
    CourseGroup,
    CourseMember,
    CourseRole,
)
from computor_backend.model.organization import Organization
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.redis_cache import get_redis_client


@pytest.fixture(autouse=True)
def enabled(monkeypatch):
    monkeypatch.setenv("PUBLIC_LUNA_ENABLED", "true")
    monkeypatch.setenv("PUBLIC_LUNA_WORKER_KEY", "k" * 32)


@pytest.fixture
def world():
    url = (
        f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}:"
        f"{os.getenv('POSTGRES_PASSWORD', 'postgres_secret')}@"
        f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
        f"{os.getenv('POSTGRES_PORT', '5432')}/"
        f"{os.getenv('POSTGRES_DB', 'computor')}"
    )
    try:
        engine = create_engine(url)
        connection = engine.connect()
    except OperationalError as exc:
        pytest.skip(f"Postgres unavailable: {exc}")
    transaction = connection.begin()
    db = sessionmaker(bind=connection)()
    suffix = uuid.uuid4().hex[:10]
    try:
        if db.get(CourseRole, "_student") is None:
            db.add(CourseRole(id="_student", title="Student", builtin=True))
            db.flush()
        org = Organization(
            title="Luna Test",
            organization_type="organization",
            path=Ltree(f"luna_{suffix}"),
        )
        db.add(org)
        db.flush()
        family = CourseFamily(
            title="Luna Test",
            organization_id=org.id,
            path=Ltree(f"luna_{suffix}.family"),
        )
        db.add(family)
        db.flush()
        course = Course(
            title="Public",
            course_family_id=family.id,
            organization_id=org.id,
            path=Ltree(f"luna_{suffix}.family.course"),
            public=True,
        )
        db.add(course)
        db.flush()
        group = CourseGroup(title="Students", course_id=course.id)
        db.add(group)
        db.flush()
        alice = User(
            given_name="Alice", family_name="Test", email=f"alice.{suffix}@test.local"
        )
        bob = User(
            given_name="Bob", family_name="Test", email=f"bob.{suffix}@test.local"
        )
        db.add_all([alice, bob])
        db.flush()
        db.add(
            CourseMember(
                user_id=alice.id,
                course_id=course.id,
                course_group_id=group.id,
                course_role_id="_student",
            )
        )
        kind = CourseContentKind(
            id=f"luna_{suffix}",
            title="Page",
            has_ascendants=False,
            has_descendants=False,
            submittable=False,
        )
        db.add(kind)
        db.flush()
        content_type = CourseContentType(
            slug="page", course_id=course.id, course_content_kind_id=kind.id
        )
        db.add(content_type)
        db.flush()
        content = CourseContent(
            course_id=course.id,
            course_content_type_id=content_type.id,
            path=Ltree("lesson"),
            position=1.0,
            title="Synthetic assignment",
            description="Write a loop",
        )
        db.add(content)
        db.flush()
        yield db, course, content, alice, bob
    finally:
        db.close()
        transaction.rollback()
        connection.close()
        engine.dispose()


@pytest.mark.asyncio
async def test_authorized_public_learner_only(world):
    db, course, content, alice, bob = world
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    request = LunaRequest(
        course_content_id=content.id,
        question="How does this work?",
        submitted_text="x = 1",
    )
    accepted = await submit_request(
        request, Principal(user_id=str(alice.id)), Response(), db, redis
    )
    assert accepted["state"] == "queued"
    with pytest.raises(HTTPException) as denied:
        await submit_request(
            request, Principal(user_id=str(bob.id)), Response(), db, redis
        )
    assert denied.value.status_code == 404

    content.visible = False
    db.flush()
    with pytest.raises(HTTPException) as hidden:
        _visible_assignment(db, str(alice.id), content.id)
    assert hidden.value.status_code == 404

    content.visible = True
    course.public = False
    db.flush()
    with pytest.raises(HTTPException) as private:
        _visible_assignment(db, str(alice.id), content.id)
    assert private.value.status_code == 404


@pytest.mark.asyncio
async def test_worker_principal_cannot_submit(world):
    db, _, content, alice, _ = world
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    request = LunaRequest(course_content_id=content.id, question="Synthetic")
    with pytest.raises(HTTPException) as denied:
        await submit_request(
            request,
            Principal(user_id=str(alice.id), is_service=True),
            Response(),
            db,
            redis,
        )
    assert denied.value.status_code == 403


@pytest.mark.asyncio
async def test_admission_fails_closed_if_redis_is_down(world):
    db, _, content, alice, _ = world

    class DownRedis:
        async def eval(self, *_args):
            raise RedisConnectionError("synthetic outage")

    request = LunaRequest(course_content_id=content.id, question="Synthetic")
    with pytest.raises(HTTPException) as failure:
        await submit_request(
            request, Principal(user_id=str(alice.id)), Response(), db, DownRedis()
        )
    assert failure.value.status_code == 503
    assert "synthetic outage" not in str(failure.value.detail)


def test_http_request_claim_complete_and_owner_only_status(world, monkeypatch):
    db, _, content, alice, bob = world
    monkeypatch.setenv("PUBLIC_LUNA_WORKER_KEY", "k" * 32)
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    app = FastAPI()
    app.include_router(router)
    caller = {"principal": Principal(user_id=str(alice.id))}
    app.dependency_overrides[get_current_principal] = lambda: caller["principal"]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_redis_client] = lambda: redis
    client = TestClient(app)

    accepted = client.post(
        "/requests",
        json={
            "course_content_id": str(content.id),
            "question": "Synthetic question",
            "submitted_text": "x = 1",
        },
    )
    assert accepted.status_code == 202
    assert accepted.headers["cache-control"] == "no-store"
    job_id = accepted.json()["id"]
    worker_header = {"X-Public-Luna-Worker-Key": "k" * 32}
    claim = client.post("/worker/claim", headers=worker_header)
    assert claim.status_code == 200
    assert claim.headers["cache-control"] == "no-store"
    assert claim.json()["request"] == {
        "course_content_id": str(content.id),
        "assignment": "Synthetic assignment\nWrite a loop",
        "question": "Synthetic question",
        "submitted_text": "x = 1",
    }
    done = client.post(
        f"/worker/complete/{job_id}",
        headers=worker_header,
        json={
            "lease": claim.json()["lease"],
            "state": "done",
            "answer": "Check the loop body.",
        },
    )
    assert done.status_code == 200
    assert done.headers["cache-control"] == "no-store"
    assert client.get(f"/requests/{job_id}").json() == {
        "state": "done",
        "answer": "Check the loop body.",
    }
    assert client.get(f"/requests/{job_id}").headers["cache-control"] == "no-store"
    caller["principal"] = Principal(user_id=str(bob.id))
    assert client.get(f"/requests/{job_id}").status_code == 404
