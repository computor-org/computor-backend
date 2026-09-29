"""Anonymous course catalog, GET /public/courses (issue #415).

Driven through the real FastAPI app with no credentials, against live
Postgres inside a rolled-back transaction (same pattern as
test_public_course_registration.py). Skips when Postgres is unreachable.
"""

import datetime as dt
import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import Ltree

from computor_backend.api import public_catalog
from computor_backend.database import get_db
from computor_backend.model.auth import User
from computor_backend.model.course import Course, CourseFamily, CourseGroup, CourseMember
from computor_backend.model.organization import Organization


def _database_url() -> str:
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "postgres_secret")
    name = os.environ.get("POSTGRES_DB", "computor")
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


@pytest.fixture
def db():
    try:
        engine = create_engine(_database_url())
        conn = engine.connect()
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"Postgres not reachable: {exc}")
    trans = conn.begin()
    session = sessionmaker(bind=conn)()
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        conn.close()


@pytest.fixture
def world(db):
    suffix = uuid.uuid4().hex[:10]
    org = Organization(
        title="Anon Catalog Org",
        organization_type="organization",
        path=Ltree(f"anoncat_{suffix}"),
        properties={},
    )
    db.add(org)
    db.flush()
    family = CourseFamily(
        title="Anon Catalog Family",
        path=Ltree(f"anoncat_{suffix}.family"),
        organization_id=org.id,
    )
    db.add(family)
    db.flush()
    counter = {"n": 0}

    def course(title, *, public=True, visible=None, archived=False, description=None):
        counter["n"] += 1
        c = Course(
            title=f"{title} {suffix}",
            description=description,
            language_code="de",
            path=Ltree(f"anoncat_{suffix}.family.c{counter['n']}"),
            course_family_id=family.id,
            organization_id=org.id,
            public=public,
            visible=visible,
            archived_at=dt.datetime.now(dt.timezone.utc) if archived else None,
        )
        db.add(c)
        db.flush()
        return c

    return {"org": org, "course": course, "suffix": suffix, "db": db}


@pytest.fixture
def client(db):
    from computor_backend.server import app

    def _override():
        yield db

    public_catalog.clear_public_catalog_cache()
    app.dependency_overrides[get_db] = _override
    try:
        yield TestClient(app)  # no `with`: lifespan (Temporal, Coder, ...) not started
    finally:
        app.dependency_overrides.pop(get_db, None)
        public_catalog.clear_public_catalog_cache()


def _ours(response, suffix):
    return [row for row in response.json() if row["title"].endswith(suffix)]


def test_anonymous_request_gets_200_and_only_listable_courses(world, client):
    listed = world["course"]("Listed", description="Intro", visible=True)
    world["course"]("Default visibility")  # visible NULL means visible
    world["course"]("Private", public=False)
    world["course"]("Hidden", visible=False)
    world["course"]("Archived", archived=True)

    response = client.get("/public/courses")

    assert response.status_code == 200
    rows = _ours(response, world["suffix"])
    titles = sorted(row["title"].removesuffix(" " + world["suffix"]) for row in rows)
    assert titles == ["Default visibility", "Listed"]
    listed_row = next(r for r in rows if r["id"] == str(listed.id))
    assert listed_row == {
        "id": str(listed.id),
        "title": listed.title,
        "description": "Intro",
        "language_code": "de",
    }


def test_courses_of_an_archived_organization_are_excluded(world, client):
    world["course"]("Under archived org")
    world["org"].archived_at = dt.datetime.now(dt.timezone.utc)
    world["db"].flush()

    response = client.get("/public/courses")

    assert response.status_code == 200
    assert _ours(response, world["suffix"]) == []


def test_response_carries_no_member_or_internal_data(world, client):
    course = world["course"]("With members")
    db = world["db"]
    group = CourseGroup(title="g", course_id=course.id)
    db.add(group)
    db.flush()
    user = User(given_name="Member", family_name="Secret", email=f"m.{world['suffix']}@test.local")
    db.add(user)
    db.flush()
    db.add(CourseMember(user_id=user.id, course_id=course.id,
                        course_group_id=group.id, course_role_id="_student"))
    db.flush()

    response = client.get("/public/courses")

    assert response.status_code == 200
    (row,) = _ours(response, world["suffix"])
    assert set(row) == {"id", "title", "description", "language_code"}
    body = response.text
    for secret in ("Secret", user.email, str(user.id), str(group.id),
                   str(world["org"].id), "anoncat_"):
        assert secret not in body


def test_response_is_cached_and_marked_cacheable(world, client):
    world["course"]("First")
    first = client.get("/public/courses")
    world["course"]("Added after first request")
    second = client.get("/public/courses")

    assert first.headers["cache-control"] == "public, max-age=60"
    assert [r["title"] for r in _ours(second, world["suffix"])] == [
        r["title"] for r in _ours(first, world["suffix"])
    ]
    public_catalog.clear_public_catalog_cache()
    third = client.get("/public/courses")
    assert len(_ours(third, world["suffix"])) == 2


# --- Cache freshness and refresh coalescing (PR #244 review, finding 4) ------
# DB-free: the query is replaced by a counting fake, so these always run.


def _entry(title):
    from computor_types.courses import CoursePublicCatalogEntry

    return CoursePublicCatalogEntry(id=str(uuid.uuid4()), title=title)


@pytest.fixture
def fake_catalog(monkeypatch):
    state = {"calls": 0, "rows": [_entry("A")], "delay": 0.0}

    def _list(db):
        state["calls"] += 1
        if state["delay"]:
            import time

            time.sleep(state["delay"])
        return list(state["rows"])

    clock = {"now": 1000.0}
    monkeypatch.setattr(public_catalog, "list_anonymous_catalog", _list)
    monkeypatch.setattr(public_catalog, "_clock", lambda: clock["now"])
    public_catalog.clear_public_catalog_cache()
    yield state, clock
    public_catalog.clear_public_catalog_cache()


def _call():
    from fastapi import Response

    response = Response()
    items = public_catalog.list_public_catalog(response, db=None)
    return [i.title for i in items], response.headers["cache-control"]


def test_downstream_max_age_never_outlives_the_server_snapshot(fake_catalog):
    state, clock = fake_catalog

    assert _call() == (["A"], "public, max-age=60")      # t=0: fresh snapshot
    state["rows"] = [_entry("B")]                         # t=1: course set changes
    clock["now"] += 59
    titles, header = _call()                              # t=59: stale-but-valid
    assert titles == ["A"]
    assert header == "public, max-age=1"                  # expires with the snapshot
    clock["now"] += 0.5
    assert _call()[1] == "public, max-age=0"
    clock["now"] += 0.5                                   # t=60: refreshed
    assert _call() == (["B"], "public, max-age=60")
    assert state["calls"] == 2


def test_concurrent_cold_requests_share_one_query(fake_catalog):
    from concurrent.futures import ThreadPoolExecutor

    state, _ = fake_catalog
    state["delay"] = 0.2
    with ThreadPoolExecutor(max_workers=20) as pool:
        results = list(pool.map(lambda _: _call(), range(20)))

    assert state["calls"] == 1
    assert all(titles == ["A"] for titles, _ in results)
