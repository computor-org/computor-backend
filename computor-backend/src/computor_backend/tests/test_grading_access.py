"""Per-course grading access (issue #262).

#262 asked for "per-course individual grader access": a named person may
grade one course and only that course, with no global "grade everything"
role. That grant already exists and needs no new role or table — it is a
``course_member`` row with ``course_role_id='_tutor'`` on that one course.
Keycloak supplies the identity; the grant itself lives in the database.

The two grading surfaces sit at deliberately different floors, and these
tests pin that split so neither drifts:

``_tutor``
    Grading a student's submitted work — ``create_artifact_grade`` and
    reaching the artifact behind it. This is the grant #262 is about.

``_lecturer``
    ``course_member_gradings``, the course-wide progress/statistics matrix
    over every member. That is a course-management report, not an act of
    grading, so a grader does not get it.

Because the ladder is inclusive (``_lecturer`` satisfies a ``_tutor``
floor), a lecturer, maintainer and owner can all grade; the reverse does
not hold. Cross-course isolation comes from
``CoursePermissionQueryBuilder.filter_by_course_membership``, which
constrains every membership lookup to the courses where the caller holds
the required role.

Rows are created inside a connection-level transaction that is rolled back
after each test, so the dev database is left untouched. Skips when Postgres
is unreachable — same pattern as ``test_course_access_matrix.py``.
"""

import os
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import Ltree

from computor_types.course_member_gradings import CourseMemberGradingsQuery

from computor_backend.business_logic.submissions import (
    check_artifact_access,
    create_artifact_grade,
)
from computor_backend.exceptions import (
    ForbiddenException,
    PermissionDeniedAsNotFound,
)
from computor_backend.model.artifact import SubmissionArtifact
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
from computor_backend.permissions.principal import Principal
from computor_backend.repositories.course_member_gradings_view import (
    CourseMemberGradingsViewRepository,
)


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
    """Two courses, so "the other course stays hidden" is actually testable.

    ``wsd`` is the course the grader is granted (mirroring the issue's
    "Chris on the WSD course"); ``other`` is a second course in the same
    organization that they hold no role in at all. Each course has one
    student with a submitted artifact to act on.
    """
    suffix = uuid.uuid4().hex[:10]

    def user(name):
        u = User(given_name=name, family_name="Test", email=f"{name}.{suffix}@test.local")
        db.add(u)
        return u

    grader = user("grader")
    lecturer = user("lecturer")
    student = user("student")
    other_student = user("otherstudent")
    outsider = user("outsider")
    db.flush()

    org = Organization(
        title="Grading Org",
        organization_type="organization",
        path=Ltree(f"gradingaccess_{suffix}"),
        properties={},
    )
    db.add(org)
    db.flush()

    family = CourseFamily(
        title="Grading Family",
        path=Ltree(f"gradingaccess_{suffix}.family"),
        organization_id=org.id,
    )
    db.add(family)
    db.flush()

    def course(slug, title):
        c = Course(
            title=title,
            path=Ltree(f"gradingaccess_{suffix}.family.{slug}"),
            course_family_id=family.id,
            organization_id=org.id,
        )
        db.add(c)
        return c

    wsd = course("wsd", "WSD")
    other = course("other", "Other Course")
    db.flush()

    def member(u, c, role, group=None):
        m = CourseMember(
            user_id=u.id,
            course_id=c.id,
            course_role_id=role,
            course_group_id=group.id if group else None,
        )
        db.add(m)
        return m

    def group_for(c):
        g = CourseGroup(title="G1", course_id=c.id)
        db.add(g)
        return g

    wsd_group = group_for(wsd)
    other_group = group_for(other)
    db.flush()

    # The #262 grant: a _tutor row on WSD and nothing on the other course.
    m_grader = member(grader, wsd, "_tutor")
    m_lecturer = member(lecturer, wsd, "_lecturer")
    m_student = member(student, wsd, "_student", wsd_group)
    m_other_student = member(other_student, other, "_student", other_group)
    db.flush()

    def artifact_for(c, m):
        """A submitted artifact owned by member ``m`` in course ``c``."""
        content_type = CourseContentType(
            title="Assignment",
            slug=f"assignment-{c.path.path.split('.')[-1]}-{suffix}",
            course_content_kind_id="assignment",
            course_id=c.id,
        )
        db.add(content_type)
        db.flush()

        content = CourseContent(
            title="A1",
            path=Ltree("a1"),
            course_id=c.id,
            course_content_type_id=content_type.id,
            course_content_kind_id="assignment",
            position=1.0,
            max_group_size=1,
        )
        db.add(content)
        db.flush()

        sg = SubmissionGroup(
            max_group_size=1,
            course_id=c.id,
            course_content_id=content.id,
        )
        db.add(sg)
        db.flush()

        db.add(
            SubmissionGroupMember(
                course_id=c.id,
                submission_group_id=sg.id,
                course_member_id=m.id,
            )
        )

        art = SubmissionArtifact(
            submission_group_id=sg.id,
            uploaded_by_course_member_id=m.id,
            file_size=1,
            bucket_name="submissions",
            object_key=f"{sg.id}/v1/main.py",
            version_identifier="v1",
            submit=True,
        )
        db.add(art)
        db.flush()
        return art

    wsd_artifact = artifact_for(wsd, m_student)
    other_artifact = artifact_for(other, m_other_student)

    return {
        "wsd": wsd,
        "other": other,
        "grader": grader,
        "lecturer": lecturer,
        "student": student,
        "outsider": outsider,
        "m_grader": m_grader,
        "m_lecturer": m_lecturer,
        "m_student": m_student,
        "m_other_student": m_other_student,
        "wsd_artifact": wsd_artifact,
        "other_artifact": other_artifact,
    }


def _principal(user=None, admin=False) -> Principal:
    return Principal(user_id=str(user.id) if user else None, is_admin=admin)


def _grade(graph, db, artifact, principal):
    return create_artifact_grade(
        artifact_id=artifact.id,
        grade=0.75,
        status=0,
        comment="ok",
        permissions=principal,
        db=db,
    )


class TestGradingASubmission:
    """The ``_tutor`` floor — the grant #262 is actually about."""

    def test_granted_grader_grades_in_their_course(self, graph, db):
        grade = _grade(graph, db, graph["wsd_artifact"], _principal(graph["grader"]))
        # The grade is recorded against the grader's own WSD membership, which
        # is what makes the grant per-course rather than global.
        assert str(grade.graded_by_course_member_id) == str(graph["m_grader"].id)
        assert grade.grade == 0.75

    def test_a_lecturer_is_also_a_grader(self, graph, db):
        """The ladder is inclusive: _lecturer satisfies the _tutor floor."""
        grade = _grade(graph, db, graph["wsd_artifact"], _principal(graph["lecturer"]))
        assert str(grade.graded_by_course_member_id) == str(graph["m_lecturer"].id)

    def test_even_an_admin_needs_a_membership_row_to_grade(self, graph, db):
        # Not an authorization refusal so much as a bookkeeping one: the grade
        # records its grader's course_member_id, so an admin who is not
        # enrolled has nothing to record it against. Called out in
        # get_course_member_or_403's docstring.
        with pytest.raises(ForbiddenException):
            _grade(graph, db, graph["wsd_artifact"], _principal(admin=True))

    def test_grader_cannot_grade_a_course_they_were_not_granted(self, graph, db):
        """The whole point of #262: the grant does not travel between courses."""
        with pytest.raises(ForbiddenException):
            _grade(graph, db, graph["other_artifact"], _principal(graph["grader"]))

    def test_student_cannot_grade_their_own_work(self, graph, db):
        with pytest.raises(ForbiddenException):
            _grade(graph, db, graph["wsd_artifact"], _principal(graph["student"]))

    def test_ungranted_outsider_cannot_grade(self, graph, db):
        with pytest.raises(ForbiddenException):
            _grade(graph, db, graph["wsd_artifact"], _principal(graph["outsider"]))


class TestReachingTheWorkToBeGraded:
    """Opening the artifact behind the grade, at the same ``_tutor`` floor."""

    def _access(self, graph, db, artifact, principal):
        return check_artifact_access(
            artifact.id, principal, db, action="get", require_tutor=True
        )

    def test_granted_grader_reaches_the_artifact(self, graph, db):
        art = self._access(graph, db, graph["wsd_artifact"], _principal(graph["grader"]))
        assert str(art.id) == str(graph["wsd_artifact"].id)

    def test_the_other_course_stays_hidden(self, graph, db):
        # Existence-hiding (404), not a 403: a grader with no role in that
        # course could not learn the artifact exists by any other route.
        with pytest.raises(PermissionDeniedAsNotFound):
            self._access(graph, db, graph["other_artifact"], _principal(graph["grader"]))

    def test_outsider_cannot_reach_the_artifact(self, graph, db):
        with pytest.raises(PermissionDeniedAsNotFound):
            self._access(graph, db, graph["wsd_artifact"], _principal(graph["outsider"]))


class TestCourseWideGradingStatistic:
    """``course_member_gradings`` stays a ``_lecturer`` report, not a grader one."""

    def _repo(self, db):
        repo = CourseMemberGradingsViewRepository(cache=None)
        repo._db = db
        return repo

    def test_lecturer_sees_their_courses_statistic(self, graph, db):
        repo = self._repo(db)
        repo._check_course_list_permissions(
            _principal(graph["lecturer"]), str(graph["lecturer"].id), graph["wsd"].id
        )

    def test_grader_is_denied_the_course_statistic(self, graph, db):
        """A grader grades submissions; the member statistic is course management."""
        repo = self._repo(db)
        with pytest.raises(ForbiddenException):
            repo._check_course_list_permissions(
                _principal(graph["grader"]), str(graph["grader"].id), graph["wsd"].id
            )

    def test_lecturer_is_denied_another_courses_statistic(self, graph, db):
        repo = self._repo(db)
        with pytest.raises(ForbiddenException):
            repo._check_course_list_permissions(
                _principal(graph["lecturer"]), str(graph["lecturer"].id), graph["other"].id
            )

    def test_admin_sees_any_courses_statistic(self, graph, db):
        repo = self._repo(db)
        repo._check_course_list_permissions(_principal(admin=True), None, graph["other"].id)

    def test_lecturer_sees_a_members_statistic(self, graph, db):
        repo = self._repo(db)
        repo._check_member_permissions(
            _principal(graph["lecturer"]),
            str(graph["lecturer"].id),
            graph["m_student"].id,
            CourseMemberGradingsQuery(),
        )

    def test_grader_is_denied_a_members_statistic(self, graph, db):
        repo = self._repo(db)
        with pytest.raises(ForbiddenException):
            repo._check_member_permissions(
                _principal(graph["grader"]),
                str(graph["grader"].id),
                graph["m_student"].id,
                CourseMemberGradingsQuery(),
            )

    def test_lecturer_is_denied_a_member_of_another_course(self, graph, db):
        repo = self._repo(db)
        with pytest.raises(ForbiddenException):
            repo._check_member_permissions(
                _principal(graph["lecturer"]),
                str(graph["lecturer"].id),
                graph["m_other_student"].id,
                CourseMemberGradingsQuery(),
            )
