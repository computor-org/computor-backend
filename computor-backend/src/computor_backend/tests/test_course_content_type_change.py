"""PATCH /course-contents must not flip a content's kind while it has cargo.

A lecturer could change an assignment's content type to a unit type (and vice
versa) through the generic update endpoint; nothing validated the new type at
all. The ORM listener then re-derived ``course_content_kind_id`` and
``is_submittable``, stranding whatever hung off the content: a unit turned
assignment hid its children from every tree, an assignment turned unit dropped
its deployment and submissions from all release and grading views while the
rows lived on (computor-org/issues#320).

``_validate_course_content_type_change`` now guards the PATCH: the new type
must live in the content's own course, same-kind changes stay free, and
cross-kind changes are only allowed while the content is empty — no
descendants, no assigned example, no submissions.

Runs against a live Postgres inside a rolled-back transaction, like
``test_course_access_matrix.py``. Skips when Postgres is unreachable.
"""

import os
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import Ltree

from computor_backend.business_logic.crud import _validate_course_content_type_change
from computor_backend.exceptions import BadRequestException
from computor_backend.model.course import (
    Course,
    CourseContent,
    CourseContentType,
    CourseFamily,
    SubmissionGroup,
)
from computor_backend.model.deployment import CourseContentDeployment
from computor_backend.model.organization import Organization


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
    """A course with an assignment type, two unit types, and a sibling course."""
    suffix = uuid.uuid4().hex[:10]

    org = Organization(
        title="Kind Guard Org",
        organization_type="organization",
        path=Ltree(f"kindguard_{suffix}"),
        properties={},
    )
    db.add(org)
    db.flush()

    family = CourseFamily(
        title="Kind Guard Family",
        path=Ltree(f"kindguard_{suffix}.family"),
        organization_id=org.id,
    )
    db.add(family)
    db.flush()

    course = Course(
        title="Kind Guard Course",
        path=Ltree(f"kindguard_{suffix}.family.course"),
        course_family_id=family.id,
        organization_id=org.id,
    )
    other_course = Course(
        title="Other Course",
        path=Ltree(f"kindguard_{suffix}.family.other"),
        course_family_id=family.id,
        organization_id=org.id,
    )
    db.add_all([course, other_course])
    db.flush()

    types = {}
    for key, kind in [
        ("assignment", "assignment"),
        ("assignment2", "assignment"),
        ("unit", "unit"),
        ("unit2", "unit"),
    ]:
        content_type = CourseContentType(
            title=key.capitalize(),
            slug=f"{key}-{suffix}",
            course_content_kind_id=kind,
            course_id=course.id,
        )
        db.add(content_type)
        types[key] = content_type
    foreign_type = CourseContentType(
        title="Foreign",
        slug=f"foreign-{suffix}",
        course_content_kind_id="assignment",
        course_id=other_course.id,
    )
    db.add(foreign_type)
    db.flush()
    types["foreign"] = foreign_type

    return {"course": course, "types": types}


def _add_content(db, course, content_type, path, **kwargs):
    content = CourseContent(
        title=path,
        path=Ltree(path),
        course_id=course.id,
        course_content_type_id=content_type.id,
        course_content_kind_id=content_type.course_content_kind_id,
        position=1.0,
        max_group_size=1,
        **kwargs,
    )
    db.add(content)
    db.flush()
    return content


@pytest.mark.integration
def test_same_kind_change_stays_allowed_even_when_deployed(db, course):
    content = _add_content(db, course["course"], course["types"]["assignment"], "a1")
    db.add(CourseContentDeployment(course_content_id=content.id, deployment_status="deployed"))
    db.flush()

    _validate_course_content_type_change(content, course["types"]["assignment2"].id, db)


@pytest.mark.integration
def test_keeping_the_current_type_is_a_no_op(db, course):
    content = _add_content(db, course["course"], course["types"]["assignment"], "a1")

    _validate_course_content_type_change(content, content.course_content_type_id, db)


@pytest.mark.integration
def test_cross_kind_change_is_allowed_while_the_content_is_empty(db, course):
    assignment = _add_content(db, course["course"], course["types"]["assignment"], "a1")
    unit = _add_content(db, course["course"], course["types"]["unit"], "u1")

    _validate_course_content_type_change(assignment, course["types"]["unit"].id, db)
    _validate_course_content_type_change(unit, course["types"]["assignment"].id, db)


@pytest.mark.integration
def test_a_deployed_assignment_cannot_become_a_unit(db, course):
    content = _add_content(db, course["course"], course["types"]["assignment"], "a1")
    db.add(CourseContentDeployment(course_content_id=content.id, deployment_status="deployed"))
    db.flush()

    with pytest.raises(BadRequestException) as exc:
        _validate_course_content_type_change(content, course["types"]["unit"].id, db)
    assert exc.value.error_code == "CONTENT_008"


@pytest.mark.integration
def test_an_unassigned_deployment_row_does_not_block(db, course):
    # Unassigning keeps the row for history; it must not pin the kind forever.
    content = _add_content(db, course["course"], course["types"]["assignment"], "a1")
    db.add(CourseContentDeployment(course_content_id=content.id, deployment_status="unassigned"))
    db.flush()

    _validate_course_content_type_change(content, course["types"]["unit"].id, db)


@pytest.mark.integration
def test_an_assignment_with_submissions_cannot_become_a_unit(db, course):
    content = _add_content(db, course["course"], course["types"]["assignment"], "a1")
    db.add(SubmissionGroup(
        course_id=course["course"].id,
        course_content_id=content.id,
        max_group_size=1,
    ))
    db.flush()

    with pytest.raises(BadRequestException) as exc:
        _validate_course_content_type_change(content, course["types"]["unit"].id, db)
    assert exc.value.error_code == "CONTENT_008"


@pytest.mark.integration
def test_a_unit_with_children_cannot_become_an_assignment(db, course):
    unit = _add_content(db, course["course"], course["types"]["unit"], "u1")
    _add_content(db, course["course"], course["types"]["assignment"], "u1.a1")

    with pytest.raises(BadRequestException) as exc:
        _validate_course_content_type_change(unit, course["types"]["assignment"].id, db)
    assert exc.value.error_code == "CONTENT_008"


@pytest.mark.integration
def test_a_childless_unit_can_become_an_assignment(db, course):
    # The repair path for #320: contents stranded on a unit-kind type keep
    # their (deployed) deployment row and must be movable back.
    unit = _add_content(db, course["course"], course["types"]["unit"], "u1")
    db.add(CourseContentDeployment(course_content_id=unit.id, deployment_status="deployed"))
    db.flush()

    _validate_course_content_type_change(unit, course["types"]["assignment"].id, db)


@pytest.mark.integration
def test_a_type_from_another_course_is_rejected(db, course):
    content = _add_content(db, course["course"], course["types"]["assignment"], "a1")

    with pytest.raises(BadRequestException) as exc:
        _validate_course_content_type_change(content, course["types"]["foreign"].id, db)
    assert exc.value.error_code == "VAL_001"


@pytest.mark.integration
def test_a_nonexistent_type_is_rejected(db, course):
    content = _add_content(db, course["course"], course["types"]["assignment"], "a1")

    with pytest.raises(BadRequestException):
        _validate_course_content_type_change(content, str(uuid.uuid4()), db)
