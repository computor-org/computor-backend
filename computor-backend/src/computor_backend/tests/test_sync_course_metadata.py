"""A content release reaches a course that is already deployed.

``deploy-course`` only creates courses, so the ordered course names of
data-science-python #7 never reached computor.at. ``sync_course_metadata``
reports such drift and, with ``apply``, writes the metadata part of it; an
assignment that is missing or an item the file dropped stays a reported
difference for a full release.

Runs against a live Postgres inside a rolled-back transaction, like
``test_course_content_type_change.py``. Skips when Postgres is unreachable.
"""

import os
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import Ltree

from computor_backend.model.course import (
    Course,
    CourseContent,
    CourseContentType,
    CourseFamily,
)
from computor_backend.model.organization import Organization
from computor_backend.scripts.sync_course_metadata import sync_course


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
def deployed(db):
    """A course as the first release left it: old name, one week, one assignment."""
    suffix = uuid.uuid4().hex[:10]
    org = Organization(title="Sync Org", organization_type="organization",
                       path=Ltree(f"sync_{suffix}"), properties={})
    db.add(org)
    db.flush()
    family = CourseFamily(title="Sync Family", path=Ltree(f"sync_{suffix}.family"),
                          organization_id=org.id)
    db.add(family)
    db.flush()
    course = Course(title="Data Science – Grundlagen", path=Ltree(f"sync_{suffix}.beginner"),
                    course_family_id=family.id, organization_id=org.id)
    db.add(course)
    db.flush()
    weekly = CourseContentType(slug="weekly", title="Woche", color="green",
                               course_content_kind_id="unit", course_id=course.id)
    task = CourseContentType(slug="task", title="Aufgabe", color="yellow",
                             course_content_kind_id="assignment", course_id=course.id)
    db.add_all([weekly, task])
    db.flush()
    for path, ct, title in [("week_1", weekly, "Woche 1"),
                            ("week_1.kirchhoff", task, "Kirchoff"),
                            ("week_1.dropped", task, "Gone from the file")]:
        db.add(CourseContent(title=title, path=Ltree(path), course_id=course.id,
                             course_content_type_id=ct.id, position=1.0, max_group_size=1))
    db.flush()
    return course


def _config(course):
    return {
        "name": "Data Science I – Grundlagen",
        "position": 10,
        "path": str(course.path),
        "content_types": [
            {"slug": "welcome", "kind": "unit", "title": "Einstieg", "color": "blue"},
            {"slug": "weekly", "kind": "unit", "title": "Woche", "color": "green"},
            {"slug": "task", "kind": "assignment", "title": "Aufgabe", "color": "yellow"},
        ],
        "contents": [
            {"path": "welcome", "content_type": "welcome", "title": "Willkommen",
             "description": "Hallo", "position": 0.0},
            {"path": "week_1", "content_type": "weekly", "title": "Woche 1", "contents": [
                {"path": "kirchhoff", "content_type": "task", "title": "Kirchhoff"},
                {"path": "new_task", "content_type": "task", "title": "Neu"},
            ]},
        ],
    }


def _contents(db, course):
    return {str(c.path): c for c in db.query(CourseContent).filter(CourseContent.course_id == course.id)}


@pytest.mark.integration
def test_check_reports_drift_without_writing(db, deployed):
    drift = sync_course(db, _config(deployed), apply=False)
    db.flush()
    db.refresh(deployed)

    assert deployed.title == "Data Science – Grundlagen"
    assert "welcome" not in _contents(db, deployed)
    assert len(drift.fixable) == 5  # title, position, welcome type, welcome unit, Kirchhoff
    assert sorted(drift.blocking) == [
        "week_1.dropped is deployed but not in the course file",
        "week_1.new_task missing; needs a release with its example",
    ]


@pytest.mark.integration
def test_apply_writes_metadata_and_leaves_assignments_to_a_release(db, deployed):
    sync_course(db, _config(deployed), apply=True)
    db.flush()
    db.refresh(deployed)
    contents = _contents(db, deployed)

    assert deployed.title == "Data Science I – Grundlagen"
    assert deployed.position == 10
    assert contents["week_1.kirchhoff"].title == "Kirchhoff"
    welcome = contents["welcome"]
    assert (welcome.title, welcome.description, welcome.position) == ("Willkommen", "Hallo", 0.0)
    assert welcome.is_submittable is False
    welcome_type = db.get(CourseContentType, welcome.course_content_type_id)
    assert welcome_type.properties == {}
    assert "week_1.new_task" not in contents
    assert "week_1.dropped" in contents

    again = sync_course(db, _config(deployed), apply=False)
    assert again.fixable == []
    assert len(again.blocking) == 2
