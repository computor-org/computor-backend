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
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import Ltree

from computor_backend.business_logic import course_registration
from computor_backend.business_logic.course_registration import (
    SELF_REGISTRATION_GROUP_TITLE,
    assign_self_enrolled_to_group,
    get_self_enrollment,
    leave_self_enrolled_course,
    list_public_courses,
    register_in_public_course,
    resolve_registration_group,
)
from computor_backend.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from computor_backend.model.auth import User
from computor_backend.model.course import (
    Course,
    CourseFamily,
    CourseGroup,
    CourseMember,
    CourseRole,
)
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

    # A schema made by create_all (the CI contract job) has no seeded roles.
    for role in ("_student", "_tutor", "_lecturer", "_inactive"):
        if db.get(CourseRole, role) is None:
            db.add(CourseRole(id=role, title=role.strip("_").title(), builtin=True))
    db.flush()

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

    def course(
        *, public: bool, title: str = "Course", max_self_registrations: int | None = None
    ) -> Course:
        counter["n"] += 1
        c = Course(
            title=title,
            path=Ltree(f"pubreg_{suffix}.family.course{counter['n']}"),
            course_family_id=family.id,
            organization_id=org.id,
            public=public,
            max_self_registrations=max_self_registrations,
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
        "seats_left",
        "full",
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

def test_registration_uses_the_self_enrolment_group_not_a_teaching_group(world, db):
    """Self-enrolled strangers never land in one of the course's real groups,
    neither the oldest one nor the alphabetically first (PR #210)."""
    course = world["course"](public=True)
    caller = world["user"]("joiner")
    for title in ("Zeta cohort", "Alpha cohort"):
        db.add(CourseGroup(title=title, course_id=course.id))
    db.flush()

    group = resolve_registration_group(course, _principal(caller), db)

    assert group.title == SELF_REGISTRATION_GROUP_TITLE == "Selbsteinschreibung"
    assert str(group.course_id) == str(course.id)


def test_self_enrolment_group_is_created_once(world, db):
    course = world["course"](public=True)
    caller = world["user"]("joiner")

    picks = {
        str(resolve_registration_group(course, _principal(caller), db).id)
        for _ in range(3)
    }

    assert len(picks) == 1
    assert (
        db.query(CourseGroup)
        .filter(
            CourseGroup.course_id == course.id,
            CourseGroup.title == SELF_REGISTRATION_GROUP_TITLE,
        )
        .count()
        == 1
    )


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


# ---------------------------------------------------------------------------
# Self-registration cap (max_self_registrations)
# ---------------------------------------------------------------------------

def _add_student(world, db, course: Course, name: str) -> CourseMember:
    student = world["user"](name)
    group = resolve_registration_group(course, _principal(student), db)
    member = CourseMember(
        user_id=student.id,
        course_id=course.id,
        course_group_id=group.id,
        course_role_id="_student",
    )
    db.add(member)
    db.flush()
    return member


@pytest.mark.asyncio
async def test_registration_is_refused_with_409_when_the_course_is_full(world, db):
    course = world["course"](public=True, max_self_registrations=1)
    await register_in_public_course(course.id, _principal(world["user"]("first")), db)

    with pytest.raises(ConflictException) as err:
        await register_in_public_course(course.id, _principal(world["user"]("second")), db)

    assert err.value.status_code == 409
    assert "This course is full" in str(err.value.detail)
    students = (
        db.query(CourseMember)
        .filter(CourseMember.course_id == course.id, CourseMember.course_role_id == "_student")
        .count()
    )
    assert students == 1


@pytest.mark.asyncio
async def test_students_enrolled_by_staff_use_up_seats(world, db):
    course = world["course"](public=True, max_self_registrations=2)
    _add_student(world, db, course, "imported1")
    _add_student(world, db, course, "imported2")

    with pytest.raises(ConflictException):
        await register_in_public_course(course.id, _principal(world["user"]("late")), db)


@pytest.mark.asyncio
async def test_non_student_members_do_not_use_up_seats(world, db):
    course = world["course"](public=True, max_self_registrations=1)
    tutor = world["user"]("tutor")
    db.add(CourseMember(user_id=tutor.id, course_id=course.id, course_role_id="_tutor"))
    db.flush()

    _, created = await register_in_public_course(course.id, _principal(world["user"]("s")), db)
    assert created is True


@pytest.mark.asyncio
async def test_a_null_cap_means_unlimited(world, db):
    course = world["course"](public=True, max_self_registrations=None)
    for i in range(5):
        _, created = await register_in_public_course(
            course.id, _principal(world["user"](f"s{i}")), db
        )
        assert created is True


@pytest.mark.asyncio
async def test_an_existing_member_of_a_full_course_still_gets_their_membership(world, db):
    course = world["course"](public=True, max_self_registrations=1)
    caller = world["user"]("insider")
    first, _ = await register_in_public_course(course.id, _principal(caller), db)

    again, created = await register_in_public_course(course.id, _principal(caller), db)

    assert created is False
    assert str(again.id) == str(first.id)


@pytest.mark.asyncio
async def test_catalog_reports_seats_left_and_full(world, db):
    tag = f"seats-{uuid.uuid4().hex[:8]}"
    open_course = world["course"](public=True, title=f"{tag} open")
    roomy = world["course"](public=True, title=f"{tag} roomy", max_self_registrations=3)
    full = world["course"](public=True, title=f"{tag} tight", max_self_registrations=1)
    _add_student(world, db, roomy, "r1")
    _add_student(world, db, full, "f1")

    items, _ = list_public_courses(
        CoursePublicQuery(title=tag), _principal(world["user"]("browser")), db
    )
    rows = {item.id: item for item in items}

    assert rows[str(open_course.id)].seats_left is None
    assert rows[str(open_course.id)].full is False
    assert rows[str(roomy.id)].seats_left == 2
    assert rows[str(roomy.id)].full is False
    assert rows[str(full.id)].seats_left == 0
    assert rows[str(full.id)].full is True


# ---------------------------------------------------------------------------
# Leaving and rejoining (issues#458)
# ---------------------------------------------------------------------------

def _member(db, course: Course, user: User) -> CourseMember:
    return (
        db.query(CourseMember)
        .filter(CourseMember.course_id == course.id, CourseMember.user_id == user.id)
        .one()
    )


@pytest.mark.asyncio
async def test_leaving_keeps_the_membership_but_ends_access(world, db):
    from computor_backend.permissions.core import db_get_course_claims

    course = world["course"](public=True)
    learner = world["user"]("leaver")
    member, _ = await register_in_public_course(course.id, _principal(learner), db)
    member_id = str(member.id)
    assert any(str(course.id) in value for _, value in db_get_course_claims(str(learner.id), db))

    leave_self_enrolled_course(course.id, _principal(learner), db)

    left = _member(db, course, learner)
    assert str(left.id) == member_id, "the row submissions and results hang on stays"
    assert left.course_role_id == "_inactive"
    assert left.properties["self_registered"] is True
    assert "left_at" in left.properties
    assert not any(str(course.id) in value for _, value in db_get_course_claims(str(learner.id), db))
    items, _ = list_public_courses(CoursePublicQuery(), _principal(learner), db)
    assert {i.id: i for i in items}[str(course.id)].enrolled is False
    with pytest.raises(NotFoundException):
        get_self_enrollment(course.id, _principal(learner), db)


@pytest.mark.asyncio
async def test_rejoining_restores_the_same_membership(world, db, _no_post_create):
    course = world["course"](public=True)
    learner = world["user"]("returner")
    first, _ = await register_in_public_course(course.id, _principal(learner), db)
    leave_self_enrolled_course(course.id, _principal(learner), db)

    again, created = await register_in_public_course(course.id, _principal(learner), db)

    assert created is True
    assert str(again.id) == str(first.id)
    assert again.course_role_id == "_student"
    assert again.properties == {"self_registered": True}
    assert db.get(CourseGroup, again.course_group_id).title == SELF_REGISTRATION_GROUP_TITLE
    assert len(_no_post_create) == 2, "content released meanwhile gets its submission groups"


@pytest.mark.asyncio
async def test_only_a_self_enrolled_student_can_leave(world, db):
    course = world["course"](public=True)
    staff_enrolled = _add_student(world, db, course, "imported")
    importee = db.get(User, staff_enrolled.user_id)
    lecturer = world["user"]("lecturer")
    db.add(CourseMember(user_id=lecturer.id, course_id=course.id, course_role_id="_lecturer",
                        properties={"self_registered": True}))
    db.flush()
    stranger = world["user"]("stranger")

    with pytest.raises(ForbiddenException):
        leave_self_enrolled_course(course.id, _principal(importee), db)
    with pytest.raises(ForbiddenException):
        leave_self_enrolled_course(course.id, _principal(lecturer), db)
    with pytest.raises(NotFoundException):
        leave_self_enrolled_course(course.id, _principal(stranger), db)
    assert _member(db, course, importee).course_role_id == "_student"
    assert _member(db, course, lecturer).course_role_id == "_lecturer"


@pytest.mark.asyncio
async def test_self_enrollment_status(world, db):
    course = world["course"](public=True)
    learner = world["user"]("learner")
    await register_in_public_course(course.id, _principal(learner), db)
    imported = db.get(User, _add_student(world, db, course, "imported").user_id)

    own = get_self_enrollment(course.id, _principal(learner), db)
    other = get_self_enrollment(course.id, _principal(imported), db)

    assert (own.self_registered, own.can_leave) == (True, True)
    assert (other.self_registered, other.can_leave) == (False, False)


@pytest.mark.asyncio
async def test_a_learner_who_left_frees_the_seat_and_rejoins_only_if_one_is_free(world, db):
    course = world["course"](public=True, max_self_registrations=1)
    first = world["user"]("first")
    second = world["user"]("second")
    await register_in_public_course(course.id, _principal(first), db)
    leave_self_enrolled_course(course.id, _principal(first), db)

    await register_in_public_course(course.id, _principal(second), db)

    with pytest.raises(ConflictException):
        await register_in_public_course(course.id, _principal(first), db)
    assert _member(db, course, first).course_role_id == "_inactive"


@pytest.mark.asyncio
async def test_websocket_does_not_treat_a_left_learner_as_staff(world, db):
    from computor_backend.websocket.connection_manager import ConnectionManager

    course = world["course"](public=True)
    learner = world["user"]("leaver")
    peer = _add_student(world, db, course, "peer")
    await register_in_public_course(course.id, _principal(learner), db)
    leave_self_enrolled_course(course.id, _principal(learner), db)
    group = db.get(CourseGroup, peer.course_group_id)

    manager = ConnectionManager()
    checks = [
        manager._can_access_course(_principal(learner), str(course.id), db),
        manager._can_access_course_group(_principal(learner), str(group.id), db),
        manager._can_access_course_member(_principal(learner), str(peer.id), db),
    ]
    for check in checks:
        allowed, _ = await check
        assert allowed is False


@pytest.mark.asyncio
async def test_a_left_learner_keeps_own_messages_but_not_course_wide_ones(world, db):
    from computor_backend.model.message import Message
    from computor_backend.permissions.handlers_course import MessagePermissionHandler

    course = world["course"](public=True)
    learner = world["user"]("leaver")
    lecturer = world["user"]("lecturer")
    member, _ = await register_in_public_course(course.id, _principal(learner), db)
    to_course = Message(author_id=lecturer.id, level=0, content="Hallo alle", course_id=course.id)
    to_group = Message(author_id=lecturer.id, level=0, content="Hallo Gruppe", course_group_id=member.course_group_id)
    to_learner = Message(author_id=lecturer.id, level=0, content="Hallo du", course_member_id=member.id)
    db.add_all([to_course, to_group, to_learner])
    db.flush()

    def visible() -> set[str]:
        query = MessagePermissionHandler(Message).build_query(_principal(learner), "list", db)
        ids = {str(m.id) for m in query.filter(Message.id.in_([to_course.id, to_group.id, to_learner.id]))}
        return {m.content for m in (to_course, to_group, to_learner) if str(m.id) in ids}

    assert visible() == {"Hallo alle", "Hallo Gruppe", "Hallo du"}
    leave_self_enrolled_course(course.id, _principal(learner), db)
    assert visible() == {"Hallo du"}


# ---------------------------------------------------------------------------
# Backfill of the Selbsteinschreibung group (issues#458)
# ---------------------------------------------------------------------------

def test_backfill_moves_earlier_self_enrolled_learners_once(world, db):
    course = world["course"](public=True)
    old_group = CourseGroup(title="default", course_id=course.id)
    db.add(old_group)
    db.flush()

    def member(name, role, properties):
        user = world["user"](name)
        row = CourseMember(user_id=user.id, course_id=course.id, course_group_id=old_group.id,
                           course_role_id=role, properties=properties)
        db.add(row)
        db.flush()
        return row

    joined = member("joined", "_student", {"self_registered": True})
    left = member("left", "_inactive", {"self_registered": True, "left_at": "2026-10-01T00:00:00+00:00"})
    imported = member("imported", "_student", None)

    planned = assign_self_enrolled_to_group(db, apply=False)
    mine = {m["course_member_id"] for m in planned if m["course_id"] == str(course.id)}
    assert mine == {str(joined.id), str(left.id)}
    assert db.query(CourseGroup).filter(
        CourseGroup.course_id == course.id, CourseGroup.title == SELF_REGISTRATION_GROUP_TITLE
    ).count() == 0, "a dry run writes nothing"

    assign_self_enrolled_to_group(db, apply=True)

    for row in (joined, left):
        db.refresh(row)
        assert db.get(CourseGroup, row.course_group_id).title == SELF_REGISTRATION_GROUP_TITLE
    db.refresh(imported)
    assert str(imported.course_group_id) == str(old_group.id)
    again = assign_self_enrolled_to_group(db, apply=False)
    assert not [m for m in again if m["course_id"] == str(course.id)]


@pytest.fixture
def race(monkeypatch):
    """Committed rows and real connections for lock tests (not the rollback fixture).

    A capped public course with one seat and two users, both committed so
    separate connections see them. ``run(name, user_id)`` registers in its own
    session on a thread; the post-create hook holds the *first* registration
    open (after its membership is flushed, before commit) until ``release``.
    Everything created is deleted afterwards.
    """
    import asyncio
    import threading

    import computor_backend.business_logic.course_member_post_create as hook_mod

    try:
        engine = create_engine(_database_url())
        engine.connect().close()
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"Postgres not reachable: {exc}")
    Session = sessionmaker(bind=engine)
    suffix = uuid.uuid4().hex[:10]

    setup = Session()
    if setup.get(CourseRole, "_student") is None:  # create_all schema, no seed
        setup.add(CourseRole(id="_student", title="Student", builtin=True))
        setup.flush()
    org = Organization(
        title="Race Org",
        organization_type="organization",
        path=Ltree(f"pubrace_{suffix}"),
        properties={},
    )
    setup.add(org)
    setup.flush()
    family = CourseFamily(
        title="Race Family", path=Ltree(f"pubrace_{suffix}.family"), organization_id=org.id
    )
    setup.add(family)
    setup.flush()
    course = Course(
        title="Race Course",
        path=Ltree(f"pubrace_{suffix}.family.course"),
        course_family_id=family.id,
        organization_id=org.id,
        public=True,
        max_self_registrations=1,
    )
    setup.add(course)
    users = [
        User(given_name=n, family_name="Race", email=f"{n}.{suffix}@test.local")
        for n in ("alice", "bob")
    ]
    setup.add_all(users)
    setup.commit()
    ids = {
        "course": course.id,
        "org": org.id,
        "family": family.id,
        "users": [u.id for u in users],
    }
    setup.close()

    first_holds_lock = threading.Event()
    release = threading.Event()
    held = {"done": False}

    async def _hook(member, db, permissions=None):
        if not held["done"]:
            held["done"] = True
            first_holds_lock.set()
            release.wait(timeout=30)

    monkeypatch.setattr(hook_mod, "course_member_post_create", _hook)
    results: dict[str, object] = {}

    def _register(name: str, user_id: str) -> None:
        session = Session()
        try:
            member, created = asyncio.run(
                register_in_public_course(ids["course"], Principal(user_id=user_id), session)
            )
            results[name] = (str(member.id), created)
        except Exception as exc:  # noqa: BLE001 - the outcome is the assertion
            session.rollback()
            results[name] = exc
        finally:
            session.close()

    def run(name: str, user_id: str) -> threading.Thread:
        thread = threading.Thread(target=_register, args=(name, user_id))
        thread.start()
        return thread

    try:
        yield SimpleNamespace(
            users=[str(u) for u in ids["users"]],
            run=run,
            first_holds_lock=first_holds_lock,
            release=release,
            results=results,
        )
    finally:
        release.set()
        cleanup = Session()
        cleanup.query(CourseMember).filter(CourseMember.course_id == ids["course"]).delete()
        cleanup.query(CourseGroup).filter(CourseGroup.course_id == ids["course"]).delete()
        cleanup.query(Course).filter(Course.id == ids["course"]).delete()
        cleanup.query(CourseFamily).filter(CourseFamily.id == ids["family"]).delete()
        cleanup.query(Organization).filter(Organization.id == ids["org"]).delete()
        cleanup.query(User).filter(User.id.in_(ids["users"])).delete()
        cleanup.commit()
        cleanup.close()
        engine.dispose()


def test_two_students_racing_for_the_last_seat_do_not_both_get_it(race):
    """Under READ COMMITTED bob cannot see alice's uncommitted row, so without
    the course row lock he would count zero students and take the seat too.
    With the lock he waits for alice's commit, recounts, and gets 409.
    """
    alice_id, bob_id = race.users
    a = race.run("alice", alice_id)
    assert race.first_holds_lock.wait(timeout=10), "alice never reached the hook"

    b = race.run("bob", bob_id)
    b.join(timeout=2)
    assert b.is_alive(), "bob must wait on the course row lock while alice is open"

    race.release.set()
    a.join(timeout=10)
    b.join(timeout=10)

    assert race.results["alice"][1] is True
    assert isinstance(race.results["bob"], ConflictException)
    assert race.results["bob"].status_code == 409


def test_a_concurrent_retry_by_the_same_student_gets_their_seat_not_409(race):
    """Both requests pass the pre-lock membership check; the retry then waits
    on the lock while the first takes the last seat. It must return that
    membership (created=False), not report the course full.
    """
    alice_id, _ = race.users
    first = race.run("first", alice_id)
    assert race.first_holds_lock.wait(timeout=10), "first request never reached the hook"

    retry = race.run("retry", alice_id)
    retry.join(timeout=2)
    assert retry.is_alive(), "the retry must wait on the course row lock"

    race.release.set()
    first.join(timeout=10)
    retry.join(timeout=10)

    member_id, created = race.results["first"]
    assert created is True
    assert race.results["retry"] == (member_id, False), race.results
