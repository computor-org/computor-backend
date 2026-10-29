"""Persisted course order is independent of course names and path conventions."""
import math
import uuid

import pytest
from pydantic import ValidationError
from sqlalchemy import Boolean, Column, DateTime, Float, JSON, MetaData, String, Table, create_engine
from sqlalchemy.orm import Session

from computor_backend.interfaces.course import CourseInterface, custom_permissions_course
from computor_backend.interfaces.student_courses import CourseStudentInterface
from computor_backend.model.course import Course
from computor_backend.permissions.principal import Claims, Principal
from computor_types.courses import CourseCreate, CourseQuery, CourseUpdate
from computor_types.student_courses import CourseStudentQuery
from computor_types.deployment_config import CourseConfig


@pytest.fixture
def ordered_courses():
    # Execute the real native query against a small database projection: no
    # PostgreSQL-only ltree, unrelated relationships or external service needed.
    engine = create_engine('sqlite://')
    table = Table('course', MetaData(), Column('id', String, primary_key=True),
                  Column('title', String), Column('position', Float),
                  Column('description', String), Column('language_code', String), Column('path', String),
                  Column('title_i18n', JSON), Column('description_i18n', JSON),
                  Column('organization_id', String, default='org'),
                  Column('public', Boolean, default=True), Column('visible', Boolean),
                  Column('archived_at', DateTime))
    table.create(engine)
    organization = Table('organization', MetaData(), Column('id', String, primary_key=True),
                         Column('title', String), Column('archived_at', DateTime))
    organization.create(engine)
    rows = [
        dict(id=str(uuid.UUID(int=6)), title='Alpha', position=None),
        dict(id=str(uuid.UUID(int=4)), title='Echo', position=20),
        dict(id=str(uuid.UUID(int=2)), title='Zulu', position=10),
        dict(id=str(uuid.UUID(int=5)), title='Echo', position=20),
        dict(id=str(uuid.UUID(int=1)), title='Alpha', position=10),
        dict(id=str(uuid.UUID(int=7)), title=None, position=None),
        dict(id=str(uuid.UUID(int=3)), title='Zulu', position=None),
    ]
    with engine.begin() as conn:
        conn.execute(organization.insert().values(id='org', title='Independent subjects'))
        conn.execute(table.insert(), rows)
    with Session(engine) as db:
        yield db, table
    engine.dispose()


@pytest.mark.parametrize('interface,params', [
    (CourseInterface, CourseQuery()),
    (CourseStudentInterface, CourseStudentQuery()),
    (CourseInterface, None),
    (CourseStudentInterface, None),
])
def test_native_course_lists_apply_position_then_title_and_id(ordered_courses, interface, params):
    db, _ = ordered_courses
    result = interface.search(db, db.query(Course.id, Course.title), params).all()
    assert [str(row.id) for row in result] == [str(uuid.UUID(int=i)) for i in (1, 2, 4, 5, 6, 3, 7)]


def test_order_update_persists_and_null_restores_fallback(ordered_courses):
    db, table = ordered_courses
    course_id = str(uuid.UUID(int=6))
    for position, first_id in [(0, 6), (None, 1)]:
        changes = CourseUpdate(position=position).model_dump(exclude_unset=True)
        assert changes == {'position': position}
        db.execute(table.update().where(table.c.id == course_id).values(**changes))
        db.commit()
        result = CourseInterface.search(db, db.query(Course.id, Course.title), CourseQuery()).all()
        assert str(result[0].id) == str(uuid.UUID(int=first_id))
    assert CourseUpdate().model_dump(exclude_unset=True) == {}


@pytest.mark.parametrize('value', [math.inf, -math.inf, math.nan, True, False])
@pytest.mark.parametrize('dto,base', [
    (CourseCreate, dict(path='unrelated', course_family_id='family')),
    (CourseUpdate, {}),
    (CourseConfig, dict(name='Arbitrary subject', path='unrelated')),
])
def test_course_order_rejects_nonfinite_and_boolean_values(dto, base, value):
    with pytest.raises(ValidationError):
        dto(**base, position=value)


@pytest.mark.parametrize('value', [-1.7976931348623157e308, 0, 1.7976931348623157e308])
def test_course_order_accepts_finite_float53_bounds(value):
    assert CourseCreate(path='independent', course_family_id='family', position=value).position == value
    assert CourseUpdate(position=value).position == value
    assert CourseConfig(name='Independent subject', path='independent', position=value).position == value


def test_legacy_null_positions_have_stable_title_id_fallback(ordered_courses):
    db, table = ordered_courses
    db.execute(table.update().values(position=None))
    result = CourseInterface.search(db, db.query(Course.id), None).all()
    assert [str(row.id) for row in result] == [str(uuid.UUID(int=i)) for i in (1, 6, 4, 5, 2, 3, 7)]


@pytest.mark.parametrize('role,allowed', [('_student', False), ('_tutor', False), ('_lecturer', True)])
def test_order_update_uses_existing_course_settings_permission(ordered_courses, role, allowed):
    db, table = ordered_courses
    course_id = str(uuid.UUID(int=6))
    user_id = str(uuid.uuid4())
    members = Table('course_member', MetaData(), Column('course_id', String),
                    Column('user_id', String), Column('course_role_id', String))
    members.create(db.get_bind())
    db.execute(members.insert().values(course_id=course_id, user_id=user_id, course_role_id=role))
    principal = Principal(user_id=user_id, claims=Claims(
        general={}, dependent={'course': {course_id: {role}}}))
    changes = CourseUpdate(position=10)
    permitted = custom_permissions_course(principal, db, course_id, changes)
    # CRUD restricts the requested entity by this native permission query before
    # applying the update. Use a projection to keep unrelated columns out.
    row = permitted.with_entities(Course.id).filter(Course.id == course_id).first()
    if row:
        assert changes.model_dump(exclude_unset=True) == {'position': 10}
        db.execute(table.update().where(table.c.id == str(row.id)).values(**changes.model_dump(exclude_unset=True)))
        db.commit()
    assert db.execute(table.select().where(table.c.id == course_id)).one().position == (10 if allowed else None)


def test_anonymous_catalog_preserves_order_and_exposes_positions(ordered_courses):
    from computor_backend.business_logic.course_registration import list_anonymous_catalog
    db, _ = ordered_courses
    courses = list_anonymous_catalog(db)
    assert [course.id for course in courses] == [str(uuid.UUID(int=i)) for i in (1, 2, 4, 5, 6, 3, 7)]
    assert [course.position for course in courses] == [10, 10, 20, 20, None, None, None]
