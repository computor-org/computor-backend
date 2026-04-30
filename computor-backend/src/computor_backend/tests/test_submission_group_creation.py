"""Regression tests for issue #244 SubmissionGroup creation.

Two bugs were filed against the synthetic-test-student lifecycle:

1. ``UUID has no attribute 'replace'`` when a Python ``uuid.UUID`` is
   bound to a UUID column on INSERT. SQLAlchemy 1.4's
   ``_PGUUID.bind_processor`` calls ``uuid.UUID(value)`` which trips
   the stdlib constructor's ``hex.replace('urn:', '')`` whenever the
   value is already a UUID instance. ``database.py`` patches the bind
   processor to short-circuit on UUID instances.

2. ``POST /submission-groups`` rejected payloads that did not carry
   ``course_id`` even though ``SubmissionGroupCreate`` doesn't list
   it. ``model.course`` now auto-derives ``course_id`` from
   ``course_content.course_id`` in a ``before_insert`` listener.
"""

from __future__ import annotations

import os
import uuid

import pytest

# Importing this module installs the SA UUID bind-processor patch.
import computor_backend.database  # noqa: F401

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from computor_backend.custom_types import Ltree
from computor_backend.model.auth import User
from computor_backend.model.course import (
    Course,
    CourseContent,
    CourseContentKind,
    CourseContentType,
    CourseFamily,
    CourseGroup,
    CourseMember,
    SubmissionGroup,
    SubmissionGroupMember,
)
from computor_backend.model.organization import Organization


def _pg_url() -> str:
    user = os.environ.get("POSTGRES_USER")
    password = os.environ.get("POSTGRES_PASSWORD")
    db = os.environ.get("POSTGRES_DB")
    if not (user and password and db):
        pytest.skip("postgres test environment not configured")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"


@pytest.fixture
def pg_session():
    engine = create_engine(_pg_url(), future=True)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        engine.dispose()


@pytest.fixture
def course_content(pg_session):
    """Build a minimal course + team-content fixture."""
    suffix = uuid.uuid4().hex[:8]

    # ``organization_type='community'`` avoids the ``user`` check
    # constraint that requires a back-reference into ``user``.
    org = Organization(
        path=Ltree(f"itest_{suffix}"),
        title=f"Issue-244 Org {suffix}",
        organization_type="community",
        properties={},
    )
    cf = CourseFamily(
        path=Ltree(f"itest_{suffix}.fam"),
        title="Family",
        organization=org,
        properties={},
    )
    course = Course(
        path=Ltree(f"itest_{suffix}.fam.course"),
        title="Course",
        course_family=cf,
        organization=org,
        properties={},
    )
    pg_session.add(course)
    pg_session.flush()

    kind = pg_session.query(CourseContentKind).filter_by(id="assignment").first()
    if kind is None:
        kind = CourseContentKind(
            id="assignment",
            title="Assignment",
            has_ascendants=False,
            has_descendants=False,
            submittable=True,
        )
        pg_session.add(kind)
        pg_session.flush()

    cct = CourseContentType(
        slug="task",
        title="Task",
        course_id=course.id,
        course_content_kind_id=kind.id,
        properties={},
    )
    pg_session.add(cct)
    pg_session.flush()

    cc = CourseContent(
        path=Ltree("week1"),
        title="Team Assignment",
        course_id=course.id,
        course_content_type_id=cct.id,
        position=1.0,
        max_group_size=4,
        properties={},
    )
    pg_session.add(cc)
    pg_session.flush()
    return cc


@pytest.fixture
def course_member(pg_session, course_content):
    """A student in ``course_content``'s course with no ``Account``."""
    suffix = uuid.uuid4().hex[:8]
    user = User(
        username=f"mcstudent_{suffix}",
        email=f"mcstudent_{suffix}@example.com",
        given_name="Student",
        family_name="McStudentface",
    )
    cg = CourseGroup(title="A1", course_id=course_content.course_id, properties={})
    pg_session.add_all([user, cg])
    pg_session.flush()
    cm = CourseMember(
        user_id=user.id,
        course_id=course_content.course_id,
        course_group_id=cg.id,
        course_role_id="_student",
        properties={},
    )
    pg_session.add(cm)
    pg_session.flush()
    return cm


@pytest.mark.integration
def test_submission_group_insert_accepts_uuid_instance_fks(
    pg_session, course_content, course_member
):
    # Bug #1: feed UUID instances (not strings) the way FastAPI hands
    # parsed path parameters to the ORM. Without the bind-processor
    # patch the flush below dies with
    # ``StatementError: 'UUID' object has no attribute 'replace'``.
    cc_id = uuid.UUID(str(course_content.id))
    course_id = uuid.UUID(str(course_content.course_id))
    cm_id = uuid.UUID(str(course_member.id))

    sg = SubmissionGroup(
        course_content_id=cc_id, course_id=course_id, max_group_size=4
    )
    pg_session.add(sg)
    pg_session.flush()
    pg_session.add(
        SubmissionGroupMember(
            submission_group_id=uuid.UUID(str(sg.id)),
            course_member_id=cm_id,
            course_id=course_id,
        )
    )
    pg_session.flush()


@pytest.mark.integration
def test_submission_group_derives_course_id_from_course_content(
    pg_session, course_content
):
    # Bug #2: ``SubmissionGroupCreate`` doesn't list ``course_id``;
    # the ``before_insert`` listener fills it from ``course_content``
    # so the documented payload no longer trips the NOT-NULL constraint.
    sg = SubmissionGroup(course_content_id=course_content.id, max_group_size=1)
    pg_session.add(sg)
    pg_session.flush()
    assert sg.course_id == course_content.course_id
