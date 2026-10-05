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
    from computor_backend.model import Language, CourseRole
    if db.query(Language).filter(Language.code == "de").first() is None:
        db.add(Language(code="de", name="German"))
    if db.query(CourseRole).filter(CourseRole.id == "_student").first() is None:
        db.add(CourseRole(id="_student", title="Student", builtin=True))
    db.flush()
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
def client(db, monkeypatch):
    from contextlib import contextmanager

    from computor_backend.server import app

    @contextmanager
    def _session():
        yield db

    # The route opens its own session on refresh (no request DB dependency);
    # bind that to the rolled-back test session.
    monkeypatch.setattr(public_catalog, "_session_factory", _session)
    public_catalog.clear_public_catalog_cache()
    try:
        yield TestClient(app)  # no `with`: lifespan (Temporal, Coder, ...) not started
    finally:
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
    from contextlib import nullcontext

    monkeypatch.setattr(public_catalog, "list_anonymous_catalog", _list)
    monkeypatch.setattr(public_catalog, "_session_factory", nullcontext)
    monkeypatch.setattr(public_catalog, "_clock", lambda: clock["now"])
    public_catalog.clear_public_catalog_cache()
    yield state, clock
    public_catalog.clear_public_catalog_cache()


def _call():
    from fastapi import Response

    response = Response()
    items = public_catalog.list_public_catalog(response)
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


# --- Pool starvation (PR #244 re-review) --------------------------------------
# Through the real ASGI app and the real PostgreSQL pool (no session binding).
# The request that owns the cache lock is held right after acquiring it until
# the contenders have had the chance to check out pool connections through a
# request DB dependency (`?user_id=` makes get_db() connect eagerly with SET
# LOCAL). If they could, all of them would sit on connections while queued on
# the lock, and the owner's refresh would time out on the exhausted pool (503
# after the 30 s pool timeout). With no request DB dependency, nobody holds a
# connection while waiting and everything completes promptly.


def test_lock_waiters_do_not_starve_the_pool(monkeypatch):
    import asyncio
    import threading
    import time

    import httpx
    from sqlalchemy import event

    from computor_backend import database
    from computor_backend.server import app

    try:
        with database._engine.connect():
            pass
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"Postgres not reachable: {exc}")

    pool = database._engine.pool
    contenders_n = pool.size() + pool._max_overflow  # every connection the pool has
    eager_checkouts = {"n": 0}
    all_checked_out = threading.Event()
    owner_claimed = threading.Event()
    claim = threading.Lock()

    def on_sql(conn, cursor, statement, *args):
        if statement.startswith("SET LOCAL app.user_id"):
            with claim:
                eager_checkouts["n"] += 1
                if eager_checkouts["n"] >= contenders_n:
                    all_checked_out.set()

    def clock():
        with claim:
            first = not owner_claimed.is_set()
            owner_claimed.set()
        if first:
            # Give contenders time to grab connections if the route lets them.
            all_checked_out.wait(3)
        return time.monotonic()

    event.listen(database._engine, "after_cursor_execute", on_sql)
    monkeypatch.setattr(public_catalog, "_clock", clock)
    public_catalog.clear_public_catalog_cache()

    async def scenario():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            start = time.monotonic()
            owner = asyncio.create_task(client.get("/public/courses"))
            assert await asyncio.to_thread(owner_claimed.wait, 10)
            contenders = [
                asyncio.create_task(client.get(
                    "/public/courses",
                    params={"user_id": "00000000-0000-0000-0000-000000000001"},
                ))
                for _ in range(contenders_n)
            ]
            first = await owner
            elapsed = time.monotonic() - start
            rest = await asyncio.gather(*contenders)
            return first, elapsed, rest

    try:
        first, elapsed, rest = asyncio.run(scenario())
    finally:
        event.remove(database._engine, "after_cursor_execute", on_sql)
        public_catalog.clear_public_catalog_cache()

    assert first.status_code == 200, (first.status_code, round(elapsed, 1))
    assert elapsed < 10
    assert eager_checkouts["n"] == 0
    assert {r.status_code for r in rest} == {200}
    assert pool.checkedout() == 0


def test_public_outline_is_pedagogical_and_hides_unreleased_or_hidden_content(world, client):
    from computor_backend.model.course import CourseContent, CourseContentKind, CourseContentType
    from computor_backend.model.deployment import CourseContentDeployment

    db = world["db"]
    course = world["course"]("Reader", description="Start here", visible=True)

    if db.query(CourseContentKind).filter(CourseContentKind.id == "unit").first() is None:
        db.add(CourseContentKind(
            id="unit",
            title="Unit",
            has_ascendants=True,
            has_descendants=True,
            submittable=False,
        ))
    if db.query(CourseContentKind).filter(CourseContentKind.id == "assignment").first() is None:
        db.add(CourseContentKind(
            id="assignment",
            title="Assignment",
            has_ascendants=True,
            has_descendants=False,
            submittable=True,
        ))
    db.flush()

    suffix = world["suffix"]
    unit_type = CourseContentType(
        slug=f"week_{suffix}",
        title="Week",
        color="green",
        course_content_kind_id="unit",
        course_id=course.id,
    )
    assignment_type = CourseContentType(
        slug=f"exercise_{suffix}",
        title="Exercise",
        color="yellow",
        course_content_kind_id="assignment",
        course_id=course.id,
    )
    db.add_all([unit_type, assignment_type])
    db.flush()

    week = CourseContent(
        title="Week 1",
        path=Ltree("week_1"),
        course_id=course.id,
        course_content_type_id=unit_type.id,
        course_content_kind_id="unit",
        is_submittable=False,
        position=1,
    )
    released = CourseContent(
        title="Mathematical Constants",
        path=Ltree("week_1.math_constants"),
        course_id=course.id,
        course_content_type_id=assignment_type.id,
        course_content_kind_id="assignment",
        is_submittable=True,
        position=1,
        max_group_size=1,
    )
    unreleased = CourseContent(
        title="Draft exercise",
        path=Ltree("week_1.draft"),
        course_id=course.id,
        course_content_type_id=assignment_type.id,
        course_content_kind_id="assignment",
        is_submittable=True,
        position=2,
        max_group_size=1,
    )
    hidden = CourseContent(
        title="Hidden exercise",
        path=Ltree("week_1.hidden"),
        course_id=course.id,
        course_content_type_id=assignment_type.id,
        course_content_kind_id="assignment",
        is_submittable=True,
        position=3,
        max_group_size=1,
        visible=False,
    )
    db.add_all([week, released, unreleased, hidden])
    db.flush()
    db.add(CourseContentDeployment(
        course_content_id=released.id,
        deployment_status="deployed",
        deployed_at=dt.datetime.now(dt.timezone.utc),
    ))
    db.flush()

    response = client.get(f"/public/courses/{course.id}/outline")

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == course.title
    assert body["description"] == "Start here"
    assert [item["title"] for item in body["contents"]] == [
        "Week 1",
        "Mathematical Constants",
    ]
    assert body["contents"][0]["depth"] == 0
    assert body["contents"][1]["depth"] == 1
    assert body["first_exercise_id"] == str(released.id)
    assert body["exercise_count"] == 1
    assert body["unit_count"] == 1
    assert response.headers["cache-control"] == "public, max-age=60"
