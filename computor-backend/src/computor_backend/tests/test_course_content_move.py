"""``PATCH /course-contents/{id}/move`` must survive the hierarchy trigger.

``trg_validate_course_content_hierarchy`` re-validates the parent chain of
every row whose ``path`` changes. The move used to cascade the descendants
first and repath the moved item afterwards, so while the descendants were
written their new parent did not exist yet and the trigger refused them: any
move of a unit that had children died as a database error, surfacing as a 500
(computor-org/issues#323).

The move now writes the item first and then the descendants one tree level at
a time, and mirrors the trigger's rules in Python so a bad target produces a
``CONTENT_009`` 400 instead of a raw database failure.

Runs against a live Postgres inside a rolled-back transaction, like
``test_course_content_type_change.py``. Skips when Postgres is unreachable.
"""

import os
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import Ltree

from computor_backend.business_logic.course_content_move import (
    apply_course_content_move,
    parent_path_of,
    validate_course_content_move,
)
from computor_backend.exceptions import BadRequestException
from computor_backend.model.course import (
    Course,
    CourseContent,
    CourseContentType,
    CourseFamily,
)
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
    """A course with one assignment type and one unit type."""
    suffix = uuid.uuid4().hex[:10]

    org = Organization(
        title="Move Org",
        organization_type="organization",
        path=Ltree(f"move_{suffix}"),
        properties={},
    )
    db.add(org)
    db.flush()

    family = CourseFamily(
        title="Move Family",
        path=Ltree(f"move_{suffix}.family"),
        organization_id=org.id,
    )
    db.add(family)
    db.flush()

    course = Course(
        title="Move Course",
        path=Ltree(f"move_{suffix}.family.course"),
        course_family_id=family.id,
        organization_id=org.id,
    )
    db.add(course)
    db.flush()

    types = {}
    for key, kind in [("assignment", "assignment"), ("unit", "unit")]:
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


def _add(db, course, content_type, path, position=1.0):
    content = CourseContent(
        title=path,
        path=Ltree(path),
        course_id=course["course"].id,
        course_content_type_id=course["types"][content_type].id,
        course_content_kind_id=course["types"][content_type].course_content_kind_id,
        position=position,
        max_group_size=1,
    )
    db.add(content)
    db.flush()
    return content


def _path_of(db, content_id) -> str:
    return db.execute(
        text("SELECT path::text FROM course_content WHERE id = :id"),
        {"id": str(content_id)},
    ).scalar()


def test_parent_path_of_returns_empty_for_root_nodes():
    assert parent_path_of("unit_1") == ""
    assert parent_path_of("unit_1.task_a") == "unit_1"
    assert parent_path_of("unit_1.sub.task_a") == "unit_1.sub"


@pytest.mark.integration
def test_moving_a_unit_with_children_repaths_the_whole_subtree(db, course):
    # The regression: cascading the children first made the trigger reject them
    # because their new parent did not exist yet.
    unit = _add(db, course, "unit", "unit_1")
    child = _add(db, course, "assignment", "unit_1.task_a")

    validate_course_content_move(unit, "unit_9", db)
    apply_course_content_move(db, unit, "unit_9", 5.0)
    db.flush()

    assert _path_of(db, unit.id) == "unit_9"
    assert _path_of(db, child.id) == "unit_9.task_a"


@pytest.mark.integration
def test_nesting_a_populated_unit_under_another_unit_repaths_every_level(db, course):
    # Level-by-level cascading: a grandchild may only be written after its own
    # parent has landed at the new path.
    outer = _add(db, course, "unit", "outer")
    unit = _add(db, course, "unit", "unit_1")
    sub = _add(db, course, "unit", "unit_1.sub")
    leaf = _add(db, course, "assignment", "unit_1.sub.task_a")

    validate_course_content_move(unit, "outer.unit_1", db)
    apply_course_content_move(db, unit, "outer.unit_1", 1.0)
    db.flush()

    assert _path_of(db, outer.id) == "outer"
    assert _path_of(db, unit.id) == "outer.unit_1"
    assert _path_of(db, sub.id) == "outer.unit_1.sub"
    assert _path_of(db, leaf.id) == "outer.unit_1.sub.task_a"


@pytest.mark.integration
def test_an_assignment_cannot_be_moved_below_an_assignment(db, course):
    target = _add(db, course, "assignment", "task_target")
    moving = _add(db, course, "assignment", "task_moving")

    with pytest.raises(BadRequestException) as exc:
        validate_course_content_move(moving, "task_target.task_moving", db)
    assert exc.value.error_code == "CONTENT_009"


@pytest.mark.integration
def test_moving_below_a_missing_parent_is_refused(db, course):
    moving = _add(db, course, "assignment", "task_moving")

    with pytest.raises(BadRequestException) as exc:
        validate_course_content_move(moving, "no_such_unit.task_moving", db)
    assert exc.value.error_code == "CONTENT_009"


@pytest.mark.integration
def test_moving_an_assignment_into_a_unit_is_allowed(db, course):
    unit = _add(db, course, "unit", "unit_1")
    moving = _add(db, course, "assignment", "task_moving")

    validate_course_content_move(moving, "unit_1.task_moving", db)
    apply_course_content_move(db, moving, "unit_1.task_moving", 0.5)
    db.flush()

    assert _path_of(db, moving.id) == "unit_1.task_moving"


@pytest.mark.integration
def test_moving_an_assignment_to_the_course_root_is_allowed(db, course):
    unit = _add(db, course, "unit", "unit_1")
    moving = _add(db, course, "assignment", "unit_1.task_moving")

    validate_course_content_move(moving, "task_moving", db)
    apply_course_content_move(db, moving, "task_moving", 2.0)
    db.flush()

    assert _path_of(db, moving.id) == "task_moving"


@pytest.mark.integration
def test_a_path_collision_is_refused(db, course):
    unit = _add(db, course, "unit", "unit_1")
    _add(db, course, "assignment", "unit_1.task_a")
    moving = _add(db, course, "assignment", "task_a")

    with pytest.raises(BadRequestException) as exc:
        validate_course_content_move(moving, "unit_1.task_a", db)
    assert "already exists" in exc.value.detail


@pytest.mark.integration
def test_a_unit_cannot_be_moved_into_its_own_descendant(db, course):
    unit = _add(db, course, "unit", "unit_1")
    _add(db, course, "unit", "unit_1.sub")

    with pytest.raises(BadRequestException) as exc:
        validate_course_content_move(unit, "unit_1.sub.unit_1", db)
    assert "own descendant" in exc.value.detail


@pytest.mark.integration
def test_an_invalid_path_format_is_refused(db, course):
    moving = _add(db, course, "assignment", "task_moving")

    with pytest.raises(BadRequestException) as exc:
        validate_course_content_move(moving, "Unit One", db)
    assert "path" in exc.value.detail.lower()


@pytest.mark.integration
def test_a_position_only_move_keeps_the_path(db, course):
    unit = _add(db, course, "unit", "unit_1")
    moving = _add(db, course, "assignment", "unit_1.task_a", position=1.0)

    validate_course_content_move(moving, "unit_1.task_a", db)
    apply_course_content_move(db, moving, "unit_1.task_a", 7.5)
    db.flush()

    assert _path_of(db, moving.id) == "unit_1.task_a"
    position = db.execute(
        text("SELECT position FROM course_content WHERE id = :id"),
        {"id": str(moving.id)},
    ).scalar()
    assert position == 7.5
