"""GET /course-contents must count and paginate distinct content rows.

``CourseContentPermissionHandler.build_query`` used to start its query from
``User`` and join out through ``course_member``, without pinning the row to the
requesting user. Visibility was still correct, but every content row came back
once per member of its course, so:

- ``query.count()`` (the X-Total-Count header) was inflated by roughly the class
  size, and
- ``LIMIT``/``OFFSET`` are applied in SQL *before* the ORM de-duplicates
  entities, so a page could contain a handful of distinct rows and silently skip
  content.

Runs against a live Postgres inside a rolled-back transaction, like
``test_course_access_matrix.py``. Skips when Postgres is unreachable.
"""

import os
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import Ltree

from computor_backend.model.auth import User
from computor_backend.model.course import (
    Course,
    CourseContent,
    CourseContentType,
    CourseFamily,
    CourseGroup,
    CourseMember,
)
from computor_backend.model.organization import Organization
from computor_backend.permissions.handlers_course import CourseContentPermissionHandler
from computor_backend.permissions.principal import Principal


CLASS_SIZE = 6
CONTENT_COUNT = 3


def _database_url() -> str:
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "postgres_secret")
    db = os.environ.get("POSTGRES_DB", "computor")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


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
def course_with_a_class(db):
    """One course, CONTENT_COUNT contents, CLASS_SIZE enrolled students."""
    suffix = uuid.uuid4().hex[:10]

    org = Organization(
        title="Pagination Org",
        organization_type="organization",
        path=Ltree(f"pagination_{suffix}"),
        properties={},
    )
    db.add(org)
    db.flush()

    family = CourseFamily(
        title="Pagination Family",
        path=Ltree(f"pagination_{suffix}.family"),
        organization_id=org.id,
    )
    db.add(family)
    db.flush()

    course = Course(
        title="Pagination Course",
        path=Ltree(f"pagination_{suffix}.family.course"),
        course_family_id=family.id,
        organization_id=org.id,
    )
    db.add(course)
    db.flush()

    group = CourseGroup(title="G1", course_id=course.id)
    db.add(group)
    db.flush()

    content_type = CourseContentType(
        title="Assignment",
        slug=f"assignment-{suffix}",
        course_content_kind_id="assignment",
        course_id=course.id,
    )
    db.add(content_type)
    db.flush()

    for i in range(CONTENT_COUNT):
        db.add(CourseContent(
            title=f"A{i}",
            path=Ltree(f"a{i}"),
            course_id=course.id,
            course_content_type_id=content_type.id,
            course_content_kind_id="assignment",
            position=float(i),
            max_group_size=1,
        ))

    students = []
    for i in range(CLASS_SIZE):
        user = User(
            given_name=f"student{i}",
            family_name="Test",
            email=f"student{i}.{suffix}@test.local",
        )
        db.add(user)
        db.flush()
        db.add(CourseMember(
            user_id=user.id,
            course_id=course.id,
            course_role_id="_student",
            course_group_id=group.id,
        ))
        students.append(user)
    db.flush()

    return {"course": course, "students": students}


def _query(db, user_id):
    handler = CourseContentPermissionHandler(CourseContent)
    principal = Principal(user_id=str(user_id), roles=["user"])
    return handler.build_query(principal, "list", db)


@pytest.mark.integration
def test_total_count_is_not_multiplied_by_the_class_size(db, course_with_a_class):
    """The regression: count() returned CONTENT_COUNT * CLASS_SIZE."""
    student = course_with_a_class["students"][0]
    query = _query(db, student.id)

    assert query.count() == CONTENT_COUNT


@pytest.mark.integration
def test_every_content_row_is_returned_exactly_once(db, course_with_a_class):
    student = course_with_a_class["students"][0]
    rows = _query(db, student.id).all()

    ids = [row.id for row in rows]
    assert len(ids) == CONTENT_COUNT
    assert len(set(ids)) == len(ids)


@pytest.mark.integration
def test_a_page_smaller_than_the_class_still_covers_the_content(db, course_with_a_class):
    """LIMIT is applied in SQL: duplicates used to eat the whole page."""
    student = course_with_a_class["students"][0]
    query = _query(db, student.id).order_by(CourseContent.position)

    page = query.limit(CONTENT_COUNT).offset(0).all()
    assert len({row.id for row in page}) == CONTENT_COUNT


@pytest.mark.integration
def test_a_non_member_sees_nothing(db, course_with_a_class):
    """Scoping must still hold after dropping the join."""
    outsider = User(
        given_name="outsider",
        family_name="Test",
        email=f"outsider.{uuid.uuid4().hex[:10]}@test.local",
    )
    db.add(outsider)
    db.flush()

    assert _query(db, outsider.id).count() == 0
