"""Public course catalog and student self-registration (issue #213).

Live-Postgres tests: every row is created inside a connection-level
transaction that is rolled back afterwards, so the dev database is left
untouched. Skips when Postgres is unreachable.

Deliberately NOT written against a hand-rolled fake Session. The behaviour
under test is largely *schema* behaviour — the CHECK constraint that forces a
_student to carry a course_group_id, the unique index on (user_id, course_id),
the unique index on (course_id, title) that the group race hits — and a mock
Session cannot see any of it.
"""

import os
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import Ltree

from computor_backend.business_logic import course_registration
from computor_backend.business_logic.course_registration import (
    SELF_REGISTRATION_GROUP_TITLE,
    list_public_courses,
    register_in_public_course,
    resolve_registration_group,
)
from computor_backend.exceptions import ForbiddenException, NotFoundException
from computor_backend.model.auth import User
from computor_backend.model.course import Course, CourseFamily, CourseGroup, CourseMember
from computor_backend.model.organization import Organization
from computor_backend.permissions.principal import Principal
from computor_types.courses import CoursePublicList, CoursePublicQuery


def _database_url() -> str:
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "postgres_secret")
    db = os.environ.get("POSTGRES_DB", "computor")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


@pytest.fixture
def db():
    """Session bound to an outer transaction that is always rolled back."""
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


@pytest.fixture(autouse=True)
def _no_post_create(monkeypatch):
    """Stub the post-create hook.

    The real one reaches Temporal and Redis and commits internally, which would
    break the rollback fixture. What it does is covered by the paths that
    already use it; what matters here is that it runs exactly once per created
    membership and never on the idempotent path.
    """
    calls = []

    async def _fake(member, db, permissions=None):
        calls.append(member)
        return None

    monkeypatch.setattr(course_registration, "course_member_post_create", _fake, raising=False)
    # The module imports it inside the function, so patch the source too.
    import computor_backend.business_logic.course_member_post_create as mod

    monkeypatch.setattr(mod, "course_member_post_create", _fake)
    return calls


@pytest.fixture
def world(db):
    """An organization + family, and a factory for courses and users in it."""
    suffix = uuid.uuid4().hex[:10]

    org = Organization(
        title="Public Registration Org",
        organization_type="organization",
        path=Ltree(f"pubreg_{suffix}"),
        properties={},
    )
    db.add(org)
    db.flush()

    family = CourseFamily(
        title="Public Registration Family",
        path=Ltree(f"pubreg_{suffix}.family"),
        organization_id=org.id,
    )
    db.add(family)
    db.flush()

    counter = {"n": 0}

    def course(*, public: bool, title: str = "Course") -> Course:
        counter["n"] += 1
        c = Course(
            title=title,
            path=Ltree(f"pubreg_{suffix}.family.course{counter['n']}"),
            course_family_id=family.id,
            organization_id=org.id,
            public=public,
        )
        db.add(c)
        db.flush()
        return c

    def user(name: str = "stranger") -> User:
        u = User(
            given_name=name,
            family_name="Test",
            email=f"{name}.{counter['n']}.{suffix}@test.local",
        )
        db.add(u)
        db.flush()
        return u

    return {"org": org, "family": family, "course": course, "user": user, "db": db}


def _principal(user: User) -> Principal:
    return Principal(user_id=str(user.id))


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

def test_catalog_lists_only_public_courses(world, db):
    public = world["course"](public=True, title="Open Course")
    private = world["course"](public=False, title="Closed Course")
    caller = world["user"]("browser")

    items, total = list_public_courses(CoursePublicQuery(), _principal(caller), db)

    ids = [i.id for i in items]
    assert str(public.id) in ids
    assert str(private.id) not in ids
    assert total == len(items)


def test_catalog_hides_courses_of_an_archived_organization(world, db):
    from datetime import datetime, timezone

    course = world["course"](public=True, title="Orphaned Course")
    caller = world["user"]("browser")

    items, _ = list_public_courses(CoursePublicQuery(), _principal(caller), db)
    assert str(course.id) in [i.id for i in items]

    world["org"].archived_at = datetime.now(timezone.utc)
    db.flush()

    items, _ = list_public_courses(CoursePublicQuery(), _principal(caller), db)
    assert str(course.id) not in [i.id for i in items]


def test_catalog_marks_the_callers_own_memberships(world, db):
    joined = world["course"](public=True, title="Joined Course")
    other = world["course"](public=True, title="Other Course")
    caller = world["user"]("member")

    group = CourseGroup(title="G1", course_id=joined.id)
    db.add(group)
    db.flush()
    db.add(
        CourseMember(
            user_id=caller.id,
            course_id=joined.id,
            course_role_id="_student",
            course_group_id=group.id,
        )
    )
    db.flush()

    items, _ = list_public_courses(CoursePublicQuery(), _principal(caller), db)
    by_id = {i.id: i for i in items}

    assert by_id[str(joined.id)].enrolled is True
    assert by_id[str(other.id)].enrolled is False


def test_catalog_row_carries_no_course_internals():
    """The leak guard.

    CourseList would hand a non-member `properties` — whose CoursePropertiesGet
    is extra='allow' and therefore re-exports Course.properties["gitlab"] group
    ids and repo URLs — plus the org/family ids and the grading budgets. If
    someone swaps CoursePublicList back to CourseList, this fails.
    """
    assert set(CoursePublicList.model_fields) == {
        "id",
        "title",
        "description",
        "path",
        "language_code",
        "organization_title",
        "enrolled",
    }


def test_catalog_filters_and_paginates(world, db):
    world["course"](public=True, title="Algorithms")
    world["course"](public=True, title="Algebra")
    world["course"](public=True, title="Zoology")
    caller = world["user"]("browser")

    items, total = list_public_courses(
        CoursePublicQuery(title="Alg"), _principal(caller), db
    )
    assert {i.title for i in items} == {"Algorithms", "Algebra"}
    assert total == 2

    page, total = list_public_courses(
        CoursePublicQuery(title="Alg", limit=1), _principal(caller), db
    )
    # Ordered by title, so the first page is the alphabetically first match,
    # and `total` still reports the unpaginated count.
    assert [i.title for i in page] == ["Algebra"]
    assert total == 2


# ---------------------------------------------------------------------------
# Group resolution
# ---------------------------------------------------------------------------

def test_registration_uses_the_oldest_group_not_the_alphabetical_first(world, db):
    """The bug in PR #210.

    Ordering groups by title drops self-registered strangers into whatever
    real teaching group happens to sort first.

    created_at is set explicitly rather than relying on insertion order:
    Postgres now() is fixed for the whole transaction, so two groups added in
    one transaction share a server-default timestamp to the microsecond and
    the ordering falls through to the random uuid tie-break.
    """
    from datetime import datetime, timedelta, timezone

    course = world["course"](public=True)
    caller = world["user"]("joiner")

    base = datetime.now(timezone.utc)
    older = CourseGroup(
        title="Zeta cohort", course_id=course.id, created_at=base - timedelta(days=2)
    )
    db.add(older)
    newer = CourseGroup(
        title="Alpha cohort", course_id=course.id, created_at=base - timedelta(days=1)
    )
    db.add(newer)
    db.flush()

    group = resolve_registration_group(course, _principal(caller), db)

    assert group.id == older.id, "must be the oldest group, not the alphabetical first"


def test_group_choice_is_stable_when_timestamps_tie(world, db):
    """Groups created in one batch share a created_at (transaction-scoped
    now()), so the winner is arbitrary — but it must be the SAME one every
    time, or self-registered students would scatter across the batch."""
    course = world["course"](public=True)
    caller = world["user"]("joiner")

    for title in ("Group A", "Group B", "Group C"):
        db.add(CourseGroup(title=title, course_id=course.id))
    db.flush()

    picks = {
        str(resolve_registration_group(course, _principal(caller), db).id)
        for _ in range(5)
    }
    assert len(picks) == 1


def test_registration_creates_a_default_group_when_the_course_has_none(world, db):
    course = world["course"](public=True)
    caller = world["user"]("joiner")

    group = resolve_registration_group(course, _principal(caller), db)

    assert group.title == SELF_REGISTRATION_GROUP_TITLE
    assert str(group.course_id) == str(course.id)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_registration_creates_a_student_membership(world, db, _no_post_create):
    course = world["course"](public=True)
    caller = world["user"]("joiner")

    member, created = await register_in_public_course(course.id, _principal(caller), db)

    assert created is True
    assert member.course_role_id == "_student"
    assert str(member.user_id) == str(caller.id)
    assert member.course_group_id is not None  # the _student CHECK constraint
    assert member.properties == {"self_registered": True}
    assert len(_no_post_create) == 1


@pytest.mark.asyncio
async def test_registration_works_for_a_user_with_no_roles_anywhere(world, db):
    """The regression guard for the whole feature."""
    course = world["course"](public=True)
    nobody = world["user"]("nobody")
    principal = _principal(nobody)

    assert principal.roles == [] or not principal.roles
    member, created = await register_in_public_course(course.id, principal, db)

    assert created is True
    assert member.course_role_id == "_student"


@pytest.mark.asyncio
async def test_registration_is_idempotent(world, db, _no_post_create):
    course = world["course"](public=True)
    caller = world["user"]("joiner")
    principal = _principal(caller)

    first, created_first = await register_in_public_course(course.id, principal, db)
    second, created_second = await register_in_public_course(course.id, principal, db)

    assert created_first is True
    assert created_second is False
    assert str(first.id) == str(second.id)
    assert len(_no_post_create) == 1, "the hook must not re-run for an existing member"

    rows = (
        db.query(CourseMember)
        .filter(CourseMember.course_id == course.id, CourseMember.user_id == caller.id)
        .count()
    )
    assert rows == 1


@pytest.mark.asyncio
async def test_registration_never_demotes_an_existing_member(world, db):
    """A lecturer who clicks Enrol stays a lecturer."""
    course = world["course"](public=True)
    lecturer = world["user"]("lecturer")

    group = CourseGroup(title="G1", course_id=course.id)
    db.add(group)
    db.flush()
    db.add(
        CourseMember(
            user_id=lecturer.id,
            course_id=course.id,
            course_role_id="_lecturer",
        )
    )
    db.flush()

    member, created = await register_in_public_course(
        course.id, _principal(lecturer), db
    )

    assert created is False
    assert member.course_role_id == "_lecturer"


@pytest.mark.asyncio
async def test_registration_in_a_private_course_is_not_found(world, db):
    course = world["course"](public=False)
    caller = world["user"]("joiner")

    with pytest.raises(NotFoundException):
        await register_in_public_course(course.id, _principal(caller), db)


@pytest.mark.asyncio
async def test_a_missing_course_fails_exactly_like_a_private_one(world, db):
    """Existence hiding: the two denials must be indistinguishable."""
    private = world["course"](public=False)
    caller = world["user"]("joiner")
    principal = _principal(caller)

    with pytest.raises(NotFoundException) as private_exc:
        await register_in_public_course(private.id, principal, db)
    with pytest.raises(NotFoundException) as missing_exc:
        await register_in_public_course(uuid.uuid4(), principal, db)

    assert type(private_exc.value) is type(missing_exc.value)
    assert private_exc.value.error_code == missing_exc.value.error_code


@pytest.mark.asyncio
async def test_service_accounts_cannot_self_register(world, db):
    course = world["course"](public=True)
    caller = world["user"]("agent")
    principal = Principal(user_id=str(caller.id), is_service=True)

    with pytest.raises(ForbiddenException):
        await register_in_public_course(course.id, principal, db)
