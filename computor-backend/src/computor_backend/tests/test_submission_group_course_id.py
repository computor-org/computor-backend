"""Regression test for SubmissionGroup ``course_id`` derivation.

``SubmissionGroupCreate`` does not list ``course_id`` because the
column is fully derivable from ``course_content.course_id``. The
database, however, declares ``course_id`` NOT NULL — so callers
that POST the documented payload tripped a NOT-NULL violation
(computor-org/issues#244 path 5). The model layer now fills
``course_id`` from the linked ``CourseContent`` in a
``before_insert`` listener.
"""

from __future__ import annotations

import os
import uuid

import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from computor_backend.custom_types import Ltree
from computor_backend.model.course import (
    Course,
    CourseContent,
    CourseContentKind,
    CourseContentType,
    CourseFamily,
    SubmissionGroup,
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
    suffix = uuid.uuid4().hex[:8]
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
        title="Assignment",
        course_id=course.id,
        course_content_type_id=cct.id,
        position=1.0,
        max_group_size=1,
        properties={},
    )
    pg_session.add(cc)
    pg_session.flush()
    return cc


@pytest.mark.integration
def test_submission_group_course_id_is_derived_from_course_content(
    pg_session, course_content
):
    sg = SubmissionGroup(course_content_id=course_content.id, max_group_size=1)
    pg_session.add(sg)
    pg_session.flush()
    assert sg.course_id == course_content.course_id
