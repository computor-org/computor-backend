"""Permission-matrix tests for the shared course/submission-group access ladder.

Covers ``permissions.course_access`` (the extraction of the previously
copy-pasted "group member OR tutor-and-above" blocks) against a live
Postgres database. All rows are created inside a connection-level
transaction that is rolled back after each test, so the dev database is
left untouched. Skips when Postgres is unreachable.
"""

import os
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import Ltree

from computor_backend.exceptions import ForbiddenException, PermissionDeniedAsNotFound
from computor_backend.model.auth import User
from computor_backend.model.course import (
    Course,
    CourseContent,
    CourseContentType,
    CourseFamily,
    CourseGroup,
    CourseMember,
    SubmissionGroup,
    SubmissionGroupMember,
)
from computor_backend.model.organization import Organization
from computor_backend.permissions.course_access import (
    get_course_member_or_403,
    require_submission_group_access,
)
from computor_backend.permissions.principal import Principal

# Needs a live Postgres (the ``db`` fixture builds a real engine below).
# Deselected from the hermetic default run; exercise with `-m integration`.
pytestmark = pytest.mark.integration


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


@pytest.fixture
def graph(db):
    """Course with one submission group and four differently-privileged users."""
    suffix = uuid.uuid4().hex[:10]

    def user(name):
        u = User(given_name=name, family_name="Test", email=f"{name}.{suffix}@test.local")
        db.add(u)
        return u

    group_student = user("groupstudent")
    other_student = user("otherstudent")
    tutor = user("tutor")
    outsider = user("outsider")
    db.flush()

    org = Organization(
        title="AccessMatrix Org",
        organization_type="organization",
        path=Ltree(f"accessmatrix_{suffix}"),
        properties={},
    )
    db.add(org)
    db.flush()

    family = CourseFamily(
        title="AccessMatrix Family",
        path=Ltree(f"accessmatrix_{suffix}.family"),
        organization_id=org.id,
    )
    db.add(family)
    db.flush()

    course = Course(
        title="AccessMatrix Course",
        path=Ltree(f"accessmatrix_{suffix}.family.course"),
        course_family_id=family.id,
        organization_id=org.id,
    )
    db.add(course)
    db.flush()

    course_group = CourseGroup(title="G1", course_id=course.id)
    db.add(course_group)
    db.flush()

    def member(u, role, group=None):
        m = CourseMember(
            user_id=u.id,
            course_id=course.id,
            course_role_id=role,
            course_group_id=group.id if group else None,
        )
        db.add(m)
        return m

    m_group_student = member(group_student, "_student", course_group)
    m_other_student = member(other_student, "_student", course_group)
    m_tutor = member(tutor, "_tutor")
    db.flush()

    content_type = CourseContentType(
        title="Assignment",
        slug=f"assignment-{suffix}",
        course_content_kind_id="assignment",
        course_id=course.id,
    )
    db.add(content_type)
    db.flush()

    content = CourseContent(
        title="A1",
        path=Ltree("a1"),
        course_id=course.id,
        course_content_type_id=content_type.id,
        course_content_kind_id="assignment",
        position=1.0,
        max_group_size=1,
    )
    db.add(content)
    db.flush()

    sg = SubmissionGroup(
        max_group_size=1,
        course_id=course.id,
        course_content_id=content.id,
    )
    db.add(sg)
    db.flush()

    db.add(
        SubmissionGroupMember(
            course_id=course.id,
            submission_group_id=sg.id,
            course_member_id=m_group_student.id,
        )
    )
    db.flush()

    return {
        "course": course,
        "submission_group": sg,
        "group_student": group_student,
        "other_student": other_student,
        "tutor": tutor,
        "outsider": outsider,
        "m_group_student": m_group_student,
        "m_other_student": m_other_student,
        "m_tutor": m_tutor,
    }


def _principal(user=None, admin=False) -> Principal:
    return Principal(user_id=str(user.id) if user else None, is_admin=admin)


class TestRequireSubmissionGroupAccess:
    # TASK-209: denial now hides existence, so the ladder raises
    # PermissionDeniedAsNotFound (a 404 NotFoundException subclass) by default
    # rather than a 403 ForbiddenException. The allow/deny DECISION is unchanged.
    def _call(self, graph, db, principal, **kw):
        require_submission_group_access(
            principal,
            graph["submission_group"].id,
            graph["course"].id,
            db,
            **kw,
        )

    def test_admin_allowed(self, graph, db):
        self._call(graph, db, _principal(admin=True))

    def test_group_member_allowed(self, graph, db):
        self._call(graph, db, _principal(graph["group_student"]))

    def test_tutor_allowed(self, graph, db):
        self._call(graph, db, _principal(graph["tutor"]))

    def test_other_student_denied(self, graph, db):
        with pytest.raises(PermissionDeniedAsNotFound):
            self._call(graph, db, _principal(graph["other_student"]))

    def test_outsider_denied(self, graph, db):
        with pytest.raises(PermissionDeniedAsNotFound):
            self._call(graph, db, _principal(graph["outsider"]))

    def test_userless_principal_denied(self, graph, db):
        with pytest.raises(PermissionDeniedAsNotFound):
            self._call(graph, db, _principal())

    def test_student_floor_allows_other_student(self, graph, db):
        # With a _student floor, any course member passes even without
        # group membership (check_artifact_access require_tutor=False mode).
        self._call(graph, db, _principal(graph["other_student"]), min_course_role="_student")

    def test_student_floor_still_denies_outsider(self, graph, db):
        with pytest.raises(PermissionDeniedAsNotFound):
            self._call(graph, db, _principal(graph["outsider"]), min_course_role="_student")

    def test_denial_status_code_is_404(self, graph, db):
        # The hide surface must be a real 404 (indistinguishable from not-found).
        with pytest.raises(PermissionDeniedAsNotFound) as exc:
            self._call(graph, db, _principal(graph["outsider"]))
        assert exc.value.status_code == 404


class TestGetCourseMemberOr403:
    def test_student_gets_own_membership(self, graph, db):
        member = get_course_member_or_403(
            _principal(graph["group_student"]), graph["course"].id, db
        )
        assert member.id == graph["m_group_student"].id

    def test_tutor_floor_denies_student(self, graph, db):
        with pytest.raises(ForbiddenException):
            get_course_member_or_403(
                _principal(graph["group_student"]),
                graph["course"].id,
                db,
                min_course_role="_tutor",
            )

    def test_tutor_floor_returns_tutor(self, graph, db):
        member = get_course_member_or_403(
            _principal(graph["tutor"]), graph["course"].id, db, min_course_role="_tutor"
        )
        assert member.id == graph["m_tutor"].id

    def test_outsider_denied(self, graph, db):
        with pytest.raises(ForbiddenException):
            get_course_member_or_403(
                _principal(graph["outsider"]), graph["course"].id, db
            )

    def test_admin_without_membership_denied(self, graph, db):
        # Admins bypass filters but still need a membership row when the
        # result is recorded on created rows (reviewer/grader identity).
        with pytest.raises(ForbiddenException):
            get_course_member_or_403(
                _principal(graph["outsider"], admin=True), graph["course"].id, db
            )

    def test_default_denial_stays_403(self, graph, db):
        # Back-compat: without an explicit exception, denial is still a 403.
        with pytest.raises(ForbiddenException) as exc:
            get_course_member_or_403(_principal(graph["outsider"]), graph["course"].id, db)
        assert exc.value.status_code == 403

    def test_hide_existence_opt_in_raises_404(self, graph, db):
        # TASK-209: call sites that hide existence pass exception=
        # PermissionDeniedAsNotFound and get a 404 without changing who is allowed.
        with pytest.raises(PermissionDeniedAsNotFound) as exc:
            get_course_member_or_403(
                _principal(graph["outsider"]),
                graph["course"].id,
                db,
                exception=PermissionDeniedAsNotFound,
            )
        assert exc.value.status_code == 404
