"""DELETE /course-content-types/{id} must explain itself, not leak SQL.

``course_content.course_content_type_id`` and ``result.course_content_type_id``
are NOT NULL with ``ondelete='RESTRICT'``, and the ORM relationships on
``CourseContentType`` carry no ``passive_deletes``. So deleting a type that is
still in use made SQLAlchemy NULL the children first, and Postgres refused with
a ``NotNullViolation``.

``delete_entity`` meant to translate that, but its guard tested
``'NotNullViolation' in str(e.orig)`` — and ``str()`` of a psycopg2 error is the
SQL message alone, never the class name. The branch was dead, so every such
delete fell through to the generic handler, which echoed the driver's text back
to the lecturer:

    Cannot delete this item due to data integrity constraints. Error: null value
    in column "course_content_type_id" of relation "course_content" violates
    not-null constraint

That is computor-org/issues#387. ``_validate_course_content_type_deletion`` now
refuses up front with ``CONTENT_010`` and names the contents in the way, and the
generic handler dispatches on the exception class instead of its message.

Runs against a live Postgres inside a rolled-back transaction, like
``test_course_content_type_change.py``. Skips when Postgres is unreachable.
"""

import os
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import Ltree

from computor_backend.business_logic.crud import _validate_course_content_type_deletion
from computor_backend.exceptions import BadRequestException
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
from computor_backend.model.result import Result


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
def course(db):
    """A course with one unit type and one assignment type."""
    suffix = uuid.uuid4().hex[:10]

    org = Organization(
        title="Type Delete Org",
        organization_type="organization",
        path=Ltree(f"typedelete_{suffix}"),
        properties={},
    )
    db.add(org)
    db.flush()

    family = CourseFamily(
        title="Type Delete Family",
        path=Ltree(f"typedelete_{suffix}.family"),
        organization_id=org.id,
    )
    db.add(family)
    db.flush()

    course = Course(
        title="Type Delete Course",
        path=Ltree(f"typedelete_{suffix}.family.course"),
        course_family_id=family.id,
        organization_id=org.id,
    )
    db.add(course)
    db.flush()

    types = {}
    for key, kind in [("unit", "unit"), ("assignment", "assignment")]:
        content_type = CourseContentType(
            title=key.capitalize(),
            slug=f"{key}-{suffix}",
            course_content_kind_id=kind,
            course_id=course.id,
        )
        db.add(content_type)
        types[key] = content_type
    db.flush()

    return {"course": course, "types": types}


def _add_content(db, course, content_type, path, title=None):
    content = CourseContent(
        title=title if title is not None else path,
        path=Ltree(path),
        course_id=course.id,
        course_content_type_id=content_type.id,
        course_content_kind_id=content_type.course_content_kind_id,
        position=1.0,
        max_group_size=1,
    )
    db.add(content)
    db.flush()
    return content


@pytest.mark.integration
def test_an_unused_type_can_be_deleted(db, course):
    _validate_course_content_type_deletion(course["types"]["unit"], db)


@pytest.mark.integration
def test_a_type_still_used_by_content_is_refused(db, course):
    _add_content(db, course["course"], course["types"]["unit"], "u1", title="Week 1")

    with pytest.raises(BadRequestException) as exc:
        _validate_course_content_type_deletion(course["types"]["unit"], db)

    assert exc.value.error_code == "CONTENT_010"
    assert "Week 1" in exc.value.detail
    assert "Unit" in exc.value.detail


@pytest.mark.integration
def test_the_refusal_never_leaks_the_database_error(db, course):
    # The whole point of #387: no column names, no driver text.
    _add_content(db, course["course"], course["types"]["unit"], "u1", title="Week 1")

    with pytest.raises(BadRequestException) as exc:
        _validate_course_content_type_deletion(course["types"]["unit"], db)

    detail = exc.value.detail
    assert "violates" not in detail
    assert "null value in column" not in detail
    assert "course_content_type_id" not in detail


@pytest.mark.integration
def test_content_without_a_title_falls_back_to_its_path(db, course):
    _add_content(db, course["course"], course["types"]["unit"], "u1", title=None)

    with pytest.raises(BadRequestException) as exc:
        _validate_course_content_type_deletion(course["types"]["unit"], db)

    assert "'u1'" in exc.value.detail


@pytest.mark.integration
def test_many_blocking_contents_are_summarised(db, course):
    for i in range(8):
        _add_content(db, course["course"], course["types"]["unit"], f"u{i}", title=f"Week {i}")

    with pytest.raises(BadRequestException) as exc:
        _validate_course_content_type_deletion(course["types"]["unit"], db)

    detail = exc.value.detail
    assert "8 course content items" in detail
    assert "and 3 more" in detail
    assert exc.value.context["course_content_count"] == 8


@pytest.mark.integration
def test_only_the_type_under_deletion_blocks(db, course):
    # Content on a different type must not pin this one.
    _add_content(db, course["course"], course["types"]["assignment"], "a1", title="Task 1")

    _validate_course_content_type_deletion(course["types"]["unit"], db)


@pytest.mark.integration
def test_a_type_held_only_by_a_stored_result_is_refused(db, course):
    """The case the extension's client-side pre-check structurally cannot see.

    A result carries its own ``course_content_type_id``, so a type can outlive
    every course content that ever wore it and still block the delete. Only the
    server sees this, which is why it stays the authority.
    """
    content = _add_content(db, course["course"], course["types"]["assignment"], "a1", title="Task 1")

    user = User(given_name="Result", family_name="Owner", email=f"result.{uuid.uuid4().hex[:8]}@test.local")
    db.add(user)
    db.flush()
    # A _student member must sit in a group (course_member_check).
    group = CourseGroup(title="G1", course_id=course["course"].id)
    db.add(group)
    db.flush()
    member = CourseMember(
        user_id=user.id,
        course_id=course["course"].id,
        course_group_id=group.id,
        course_role_id="_student",
    )
    db.add(member)
    db.flush()

    # The result points at the assignment content but at the *unit* type.
    db.add(Result(
        course_member_id=member.id,
        course_content_id=content.id,
        course_content_type_id=course["types"]["unit"].id,
        version_identifier="c0ffee",
        status=0,
    ))
    db.flush()

    with pytest.raises(BadRequestException) as exc:
        _validate_course_content_type_deletion(course["types"]["unit"], db)

    assert exc.value.error_code == "CONTENT_010"
    assert "stored test result" in exc.value.detail
    assert exc.value.context["course_content_count"] == 0
    assert exc.value.context["result_count"] == 1
