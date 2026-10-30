"""Lena unit-description drafts (computor-org/issues#559).

Permissions and job input against the real PostgreSQL schema; the queue on
fakeredis. Assignment texts are read from MinIO in production; here the
storage reader is replaced, and its file filter is tested on its own.
"""

import json
import os
import uuid
from types import SimpleNamespace

import fakeredis.aioredis
import pytest
from fastapi import FastAPI, Response
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import Ltree

from computor_backend.api import course_content_description_drafts as api
from computor_backend.business_logic import course_content_description_draft as logic
from computor_backend.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
    RateLimitException,
    ServiceUnavailableException,
)
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
from computor_backend.services import description_draft_queue as queue
from computor_backend.settings import settings
from computor_types.course_content_description_drafts import (
    DescriptionDraftCompletion,
    DescriptionDraftRequest,
)


@pytest.fixture
def redis():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
def world(monkeypatch):
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
        for role in ("_lecturer", "_tutor", "_student"):
            if db.get(CourseRole, role) is None:
                db.add(CourseRole(id=role, title=role.strip("_").title(), builtin=True))
        db.flush()
        org = Organization(
            title="Draft Test", organization_type="organization", path=Ltree(f"draft_{suffix}")
        )
        db.add(org)
        db.flush()
        family = CourseFamily(
            title="Draft Test", organization_id=org.id, path=Ltree(f"draft_{suffix}.family")
        )
        db.add(family)
        db.flush()
        course = Course(
            title="Programming 1",
            course_family_id=family.id,
            organization_id=org.id,
            path=Ltree(f"draft_{suffix}.family.course"),
        )
        db.add(course)
        db.flush()
        group = CourseGroup(title="Group", course_id=course.id)
        db.add(group)
        db.flush()
        users = {
            name: User(given_name=name.title(), family_name="Sentinel", email=f"{name}.{suffix}@test.local")
            for name in ("lecturer", "tutor", "student", "lena")
        }
        db.add_all(users.values())
        db.flush()
        for name, role in (("lecturer", "_lecturer"), ("tutor", "_tutor"), ("student", "_student")):
            db.add(CourseMember(
                user_id=users[name].id, course_id=course.id,
                course_group_id=group.id, course_role_id=role,
            ))
        unit_kind = CourseContentKind(
            id=f"unit_{suffix}", title="Unit",
            has_ascendants=False, has_descendants=True, submittable=False,
        )
        task_kind = CourseContentKind(
            id=f"task_{suffix}", title="Assignment",
            has_ascendants=True, has_descendants=False, submittable=True,
        )
        db.add_all([unit_kind, task_kind])
        db.flush()
        unit_type = CourseContentType(
            slug="week", title="Week", course_id=course.id, course_content_kind_id=unit_kind.id
        )
        task_type = CourseContentType(
            slug="exercise", title="Exercise", course_id=course.id, course_content_kind_id=task_kind.id
        )
        db.add_all([unit_type, task_type])
        db.flush()

        def content(path, title, content_type, position, **extra):
            row = CourseContent(
                course_id=course.id, course_content_type_id=content_type.id,
                path=Ltree(path), position=position, title=title, **extra,
            )
            db.add(row)
            db.flush()
            return row

        unit = content("week1", "Week 1", unit_type, 1.0, description="Old text")
        empty_unit = content("week2", "Week 2", unit_type, 2.0)
        loops = content("week1.loops", "Loops", task_type, 1.0)
        lists = content("week1.lists", "Lists", task_type, 2.0, description="Lecturer note on lists")
        archived = content("week1.old", "Old", task_type, 3.0)
        archived.archived_at = archived.created_at
        db.flush()

        texts = {
            str(loops.id): {"de": "Schleifen", "en": "Write a for loop"},
            str(lists.id): {},
            str(archived.id): {"en": "archived text"},
        }

        async def fake_texts(row, _db, _storage):
            return texts.get(str(row.id), {})

        monkeypatch.setattr(logic, "_assignment_texts", fake_texts)
        monkeypatch.setattr(settings, "TUTOR_AGENT_USER_ID", str(users["lena"].id))
        yield SimpleNamespace(
            db=db, course=course, unit=unit, empty_unit=empty_unit, loops=loops,
            lists=lists, users=users,
        )
    finally:
        db.close()
        transaction.rollback()
        connection.close()
        engine.dispose()


def principal(world, name, **extra):
    return Principal(user_id=str(world.users[name].id), **extra)


async def ask(world, redis, name="lecturer", content=None, body=None):
    return await api.request_description_draft(
        (content or world.unit).id,
        body or DescriptionDraftRequest(),
        principal(world, name),
        Response(),
        world.db,
        redis,
        None,
    )


async def worker_alive(redis):
    # The first claim marks Lena's worker as alive.
    assert (await queue.claim(redis)) is None


@pytest.mark.asyncio
async def test_lecturer_gets_job_with_assignment_text_only(world, redis):
    await worker_alive(redis)
    job = await ask(world, redis, body=DescriptionDraftRequest(instruction="  Keep it short  "))
    assert job.state == "queued"

    claim = await api.claim_description_draft(principal(world, "lena"), Response(), redis)
    assert claim.state == "claimed" and claim.id == job.id
    request = claim.request
    assert request.unit_title == "Week 1"
    assert request.unit_description == "Old text"
    assert request.course_title == "Programming 1"
    assert request.instruction == "Keep it short"
    assert request.languages == ["de", "en"]
    assert [(a.title, a.content_type, a.text, a.text_language) for a in request.assignments] == [
        ("Loops", "Exercise", "Schleifen", "de"),
        ("Lists", "Exercise", "Lecturer note on lists", None),
    ]
    # Nobody's name, address or id reaches the worker.
    dumped = json.dumps(claim.model_dump())
    for user in world.users.values():
        assert user.email not in dumped and str(user.id) not in dumped
    assert "Sentinel" not in dumped

    done = await api.complete_description_draft(
        uuid.UUID(job.id),
        DescriptionDraftCompletion(
            lease=claim.lease, state="done",
            drafts=[
                {"language": "en", "description": "Week 1 covers loops and lists."},
                {"language": "de", "description": "Woche 1: Schleifen und Listen."},
            ],
        ),
        principal(world, "lena"), Response(), redis,
    )
    assert done == {"state": "finished"}
    result = await api.get_description_draft(uuid.UUID(job.id), principal(world, "lecturer"), Response(), redis)
    assert result.state == "done"
    assert {d.language: d.description for d in result.drafts}["de"].startswith("Woche 1")
    # The draft is never written to the unit.
    world.db.refresh(world.unit)
    assert world.unit.description == "Old text"

    with pytest.raises(NotFoundException):
        await api.get_description_draft(uuid.UUID(job.id), principal(world, "tutor"), Response(), redis)


@pytest.mark.asyncio
async def test_requested_languages_and_course_language_fallback(world, redis):
    await worker_alive(redis)
    await ask(world, redis, body=DescriptionDraftRequest(languages=["EN"]))
    claim = await queue.claim(redis)
    assert claim[2]["request"]["languages"] == ["en"]
    assert claim[2]["request"]["assignments"][0]["text"] == "Write a for loop"


@pytest.mark.asyncio
async def test_only_lecturers_may_ask(world, redis):
    await worker_alive(redis)
    for name in ("tutor", "student", "lena"):
        with pytest.raises(ForbiddenException):
            await ask(world, redis, name=name)


@pytest.mark.asyncio
async def test_units_with_assignments_only(world, redis):
    await worker_alive(redis)
    with pytest.raises(BadRequestException):
        await ask(world, redis, content=world.loops)
    with pytest.raises(BadRequestException):
        await ask(world, redis, content=world.empty_unit)


@pytest.mark.asyncio
async def test_unavailable_without_worker_or_tutor_agent(world, redis, monkeypatch):
    with pytest.raises(ServiceUnavailableException):
        await ask(world, redis)
    await worker_alive(redis)
    availability = await api.get_description_draft_availability(principal(world, "lecturer"), world.db, redis)
    assert availability.enabled is True
    monkeypatch.setattr(settings, "TUTOR_AGENT_USER_ID", None)
    availability = await api.get_description_draft_availability(principal(world, "lecturer"), world.db, redis)
    assert availability.enabled is False
    with pytest.raises(ServiceUnavailableException):
        await ask(world, redis)


@pytest.mark.asyncio
async def test_one_pending_draft_per_lecturer(world, redis):
    await worker_alive(redis)
    await ask(world, redis)
    with pytest.raises(RateLimitException):
        await ask(world, redis)


@pytest.mark.asyncio
async def test_only_lena_claims_and_completes(world, redis):
    await worker_alive(redis)
    job = await ask(world, redis)
    with pytest.raises(ForbiddenException):
        await api.claim_description_draft(principal(world, "lecturer", is_admin=True), Response(), redis)
    claim = await api.claim_description_draft(principal(world, "lena"), Response(), redis)
    completion = DescriptionDraftCompletion(lease=claim.lease, state="failed", error="too_long")
    with pytest.raises(ForbiddenException):
        await api.complete_description_draft(uuid.UUID(job.id), completion, principal(world, "lecturer"), Response(), redis)
    await api.complete_description_draft(uuid.UUID(job.id), completion, principal(world, "lena"), Response(), redis)
    result = await api.get_description_draft(uuid.UUID(job.id), principal(world, "lecturer"), Response(), redis)
    assert (result.state, result.error, result.drafts) == ("failed", "too_long", None)


@pytest.mark.asyncio
async def test_completion_must_match_requested_languages(world, redis):
    await worker_alive(redis)
    job = await ask(world, redis)
    claim = await api.claim_description_draft(principal(world, "lena"), Response(), redis)
    with pytest.raises(BadRequestException):
        await api.complete_description_draft(
            uuid.UUID(job.id),
            DescriptionDraftCompletion(
                lease=claim.lease, state="done", drafts=[{"language": "en", "description": "Only English"}]
            ),
            principal(world, "lena"), Response(), redis,
        )
    with pytest.raises(BadRequestException):
        await api.complete_description_draft(
            uuid.UUID(job.id),
            DescriptionDraftCompletion(
                lease=claim.lease, state="failed",
                drafts=[{"language": "en", "description": "x"}],
            ),
            principal(world, "lena"), Response(), redis,
        )


def test_overlong_draft_is_rejected(monkeypatch, redis):
    lena = str(uuid.uuid4())
    monkeypatch.setattr(settings, "TUTOR_AGENT_USER_ID", lena)
    app = FastAPI()
    app.include_router(api.router, prefix="/course-contents")
    app.dependency_overrides[get_current_principal] = lambda: Principal(user_id=lena)
    app.dependency_overrides[get_redis_client] = lambda: redis
    response = TestClient(app).post(
        f"/course-contents/description-drafts/worker/complete/{uuid.uuid4()}",
        json={"lease": "1", "state": "done", "drafts": [{"language": "en", "description": "x" * 4097}]},
    )
    assert response.status_code == 422


class FakeStorage:
    def __init__(self, files):
        self.files = files
        self.downloaded = []

    async def list_objects(self, bucket_name, prefix):
        return [SimpleNamespace(object_name=name) for name in self.files if name.startswith(prefix)]

    async def download_file(self, bucket_name, object_key):
        self.downloaded.append(object_key)
        return self.files[object_key]


@pytest.mark.asyncio
async def test_assignment_texts_read_only_student_description_files(monkeypatch):
    version = SimpleNamespace(
        storage_path="examples/loops/v1",
        example=SimpleNamespace(repository=SimpleNamespace(source_type="minio", source_url="bucket/examples")),
    )

    class Versions:
        def __init__(self, _db):
            pass

        def get_with_relationships(self, _version_id):
            return version

    monkeypatch.setattr(logic, "ExampleVersionRepository", Versions)
    base = "examples/loops/v1/"
    storage = FakeStorage({
        base + "content/README.md": b"readme",
        base + "content/index.md": b"default text",
        base + "content/index_de.md": b"deutscher Text",
        base + "content/index_en-gb.md": b"british",
        base + "content/meta.yaml": b"secret meta",
        base + "content/test.yaml": b"secret tests",
        base + "content/solution.md": b"secret solution",
        base + "content/tests/index.md": b"secret nested",
        base + "content/mediaFiles/plot.png": b"png",
        base + "test.yaml": b"secret root tests",
        base + "meta.yaml": b"secret root meta",
    })
    content = SimpleNamespace(
        deployment=SimpleNamespace(deployment_status="deployed", example_version_id="v1")
    )
    texts = await logic._assignment_texts(content, None, storage)
    assert texts == {"": "default text", "de": "deutscher Text", "en": "british"}
    assert all("secret" not in storage.files[key].decode() for key in storage.downloaded)

    unassigned = SimpleNamespace(
        deployment=SimpleNamespace(deployment_status="unassigned", example_version_id=None)
    )
    assert await logic._assignment_texts(unassigned, None, storage) == {}


def test_long_texts_are_shortened_to_fit():
    assert logic._shorten("abc", 10) == "abc"
    shortened = logic._shorten("x" * 100, 50)
    assert len(shortened) == 50 and shortened.endswith("[shortened]")


def test_at_most_four_languages_and_the_course_language_stays():
    texts = [{"en": "a", "fr": "b"}, {"de": "c", "es": "d", "it": "e", "": "f"}]
    course = SimpleNamespace(language_code="it")
    assert logic._draft_languages(DescriptionDraftRequest(), texts, course) == ["it", "de", "en", "es"]


@pytest.mark.asyncio
async def test_cancel_frees_the_lecturer_and_drops_the_job(redis):
    lecturer, other = str(uuid.uuid4()), str(uuid.uuid4())
    payload = {"course_content_id": "c", "request": {"languages": ["en"]}}
    outcome, job_id = await queue.admit(redis, lecturer, payload)
    assert outcome == "accepted"
    assert (await queue.admit(redis, lecturer, payload))[0] == "pending"

    # Someone else's cancel leaves the job alone.
    assert await queue.cancel(redis, other, job_id) == "other"
    assert (await queue.status(redis, lecturer, job_id))["state"] == "queued"

    _, lease, _ = await queue.claim(redis)
    assert await queue.cancel(redis, lecturer, job_id) == "cancelled"
    assert await queue.status(redis, lecturer, job_id) is None
    # Lena's late result is refused, and the lecturer can ask again at once.
    assert await queue.finish(redis, job_id, lease, {"state": "failed", "error": "model_error"}) == "expired"
    outcome, second = await queue.admit(redis, lecturer, payload)
    assert outcome == "accepted"

    # A finished draft can be dropped too, by its owner only.
    _, lease, _ = await queue.claim(redis)
    assert await queue.finish(redis, second, lease, {"state": "failed", "error": "model_error"}) == "finished"
    assert await queue.cancel(redis, other, second) == "other"
    assert await queue.cancel(redis, lecturer, second) == "cancelled"
    assert await queue.status(redis, lecturer, second) is None
    assert await queue.cancel(redis, lecturer, str(uuid.uuid4())) == "gone"


@pytest.mark.asyncio
async def test_worker_counts_as_alive_while_it_writes_a_draft(redis):
    assert await queue.worker_alive(redis) is False
    _, job_id = await queue.admit(redis, str(uuid.uuid4()), {"request": {"languages": ["en"]}})
    _, lease, _ = await queue.claim(redis)
    # A long draft: the claim's mark has expired, the lease has not.
    await redis.delete(f"{queue.PREFIX}:worker")
    assert await queue.worker_alive(redis) is True
    await queue.finish(redis, job_id, lease, {"state": "failed", "error": "model_error"})
    assert await queue.worker_alive(redis) is False


def test_cancel_answers_the_same_for_any_job(redis):
    app = FastAPI()
    app.include_router(api.router, prefix="/course-contents")
    app.dependency_overrides[get_current_principal] = lambda: Principal(user_id=str(uuid.uuid4()))
    app.dependency_overrides[get_redis_client] = lambda: redis
    response = TestClient(app).delete(f"/course-contents/description-drafts/{uuid.uuid4()}")
    assert response.status_code == 204 and response.content == b""
