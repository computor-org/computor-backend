"""Deleting a student is not blocked by the empty groups enrollment created.

Enrollment creates one submission group per assignment with the student as its
only member, and ``submission_group_member.course_member_id`` is
``ondelete='RESTRICT'``. So ``DELETE /course-members/{id}`` failed with a
NotNullViolation (the ORM tried to NULL the member rows) and ``DELETE
/users/{id}`` with a ForeignKeyViolation, even when the groups held nothing —
computor-org/issues#608. A group that holds work must still block.

Rows live in a transaction that is rolled back after each test. Skips when
Postgres is unreachable.
"""
import asyncio
import os
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import Ltree

from computor_backend.business_logic.crud import delete_entity
from computor_backend.exceptions import BadRequestException
from computor_backend.model.artifact import SubmissionArtifact
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
    SubmissionGroup,
    SubmissionGroupMember,
)
from computor_backend.model.message import Message
from computor_backend.model.organization import Organization
from computor_backend.permissions.principal import Principal

ADMIN = Principal(is_admin=True, roles=["_admin"])


def _url() -> str:
    return (
        f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}:"
        f"{os.getenv('POSTGRES_PASSWORD', 'postgres_secret')}@"
        f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
        f"{os.getenv('POSTGRES_PORT', '5432')}/"
        f"{os.getenv('POSTGRES_DB', 'computor')}"
    )


@pytest.fixture
def db():
    try:
        engine = create_engine(_url())
        conn = engine.connect()
    except OperationalError as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"Postgres unavailable: {exc}")
    trans = conn.begin()
    session = sessionmaker(bind=conn)()
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        conn.close()
        engine.dispose()


@pytest.fixture
def course(db):
    """A course with three assignments, and a helper to enroll students."""
    suffix = uuid.uuid4().hex[:10]
    if db.get(CourseRole, "_student") is None:
        db.add(CourseRole(id="_student", title="Student", builtin=True))
    kind = CourseContentKind(
        id=f"memberdel_{suffix}", title="Assignment",
        has_ascendants=False, has_descendants=False, submittable=True,
    )
    db.add(kind)
    db.flush()
    org = Organization(title="Member Delete", organization_type="organization",
                       path=Ltree(f"memberdel_{suffix}"), properties={})
    db.add(org)
    db.flush()
    family = CourseFamily(title="F", organization_id=org.id, path=Ltree(f"memberdel_{suffix}.f"))
    db.add(family)
    db.flush()
    c = Course(title="C", course_family_id=family.id, organization_id=org.id,
               path=Ltree(f"memberdel_{suffix}.f.c"))
    db.add(c)
    db.flush()
    # Students must belong to a course group (course_member_check).
    course_group = CourseGroup(title="G", course_id=c.id)
    db.add(course_group)
    content_type = CourseContentType(slug=f"a-{suffix}", course_id=c.id, course_content_kind_id=kind.id)
    db.add(content_type)
    db.flush()
    assignments = []
    for i in range(3):
        content = CourseContent(course_id=c.id, course_content_type_id=content_type.id,
                                path=Ltree(f"a{i}"), position=float(i), title=f"A{i}",
                                course_content_kind_id=kind.id, max_group_size=2, is_submittable=True)
        db.add(content)
        assignments.append(content)
    db.flush()

    def enroll(name):
        """A student with one empty single-member group per assignment, as enrollment leaves it."""
        user = User(given_name=name, family_name="Synthetic", email=f"{name}.{suffix}@test.local")
        db.add(user)
        db.flush()
        member = CourseMember(user_id=user.id, course_id=c.id, course_role_id="_student",
                              course_group_id=course_group.id)
        db.add(member)
        db.flush()
        groups = []
        for content in assignments:
            group = SubmissionGroup(max_group_size=1, course_id=c.id, course_content_id=content.id)
            db.add(group)
            db.flush()
            db.add(SubmissionGroupMember(course_id=c.id, submission_group_id=group.id,
                                         course_member_id=member.id))
            groups.append(group)
        db.flush()
        return user, member, groups

    return {"course": c, "assignments": assignments, "enroll": enroll}


def _delete(db, model, entity_id):
    asyncio.run(delete_entity(ADMIN, db, str(entity_id), model))
    db.expire_all()


def _group_count(db, group_ids):
    return db.query(SubmissionGroup).filter(SubmissionGroup.id.in_(group_ids)).count()


@pytest.mark.integration
def test_a_member_with_only_empty_groups_can_be_deleted(db, course):
    _, member, groups = course["enroll"]("ada")
    member_id, group_ids = member.id, [g.id for g in groups]

    _delete(db, CourseMember, member_id)

    assert db.get(CourseMember, member_id) is None
    assert _group_count(db, group_ids) == 0


@pytest.mark.integration
def test_a_user_with_only_empty_groups_can_be_deleted(db, course):
    user, member, groups = course["enroll"]("bob")
    user_id, member_id, group_ids = user.id, member.id, [g.id for g in groups]

    _delete(db, User, user_id)

    assert db.get(User, user_id) is None
    assert db.get(CourseMember, member_id) is None
    assert _group_count(db, group_ids) == 0


@pytest.mark.integration
def test_a_shared_empty_group_keeps_its_other_member(db, course):
    _, ada, _ = course["enroll"]("ada")
    _, bob, _ = course["enroll"]("bob")
    team = SubmissionGroup(max_group_size=2, course_id=course["course"].id,
                           course_content_id=course["assignments"][0].id)
    db.add(team)
    db.flush()
    for member in (ada, bob):
        db.add(SubmissionGroupMember(course_id=course["course"].id, submission_group_id=team.id,
                                     course_member_id=member.id))
    db.flush()

    _delete(db, CourseMember, ada.id)

    remaining = db.query(SubmissionGroupMember.course_member_id).filter(
        SubmissionGroupMember.submission_group_id == team.id,
    ).all()
    assert remaining == [(bob.id,)]


@pytest.mark.integration
@pytest.mark.parametrize("work", ["artifact", "message"])
def test_a_group_holding_work_still_blocks_and_nothing_changes(db, course, work):
    user, member, groups = course["enroll"]("cyd")
    if work == "artifact":
        db.add(SubmissionArtifact(submission_group_id=groups[1].id, uploaded_by_course_member_id=member.id,
                                  file_size=1, bucket_name="submissions",
                                  object_key=f"{groups[1].id}/{uuid.uuid4().hex}", submit=True))
    else:
        db.add(Message(title="Question", content="Why does this fail?", level=0, author_id=user.id,
                       course_id=course["course"].id, submission_group_id=groups[1].id))
    db.flush()

    for model, entity_id in ((CourseMember, member.id), (User, user.id)):
        with pytest.raises(BadRequestException) as exc:
            _delete(db, model, entity_id)
        assert "submission groups hold submissions, results or messages (groups: 1)" in exc.value.detail
        assert "violates" not in exc.value.detail

    assert db.get(CourseMember, member.id) is not None
    assert _group_count(db, [g.id for g in groups]) == 3
