"""Course files carry per-language titles to a deployed course (issues#550).

A course file without ``title_i18n``/``description_i18n``/``language_code``
deploys exactly as before; one with them stores the maps on the course, its
content types and its contents, and fills ``course.language_code``.

Runs ``deploy_course_from_config`` against a live Postgres inside a
rolled-back transaction, like ``test_sync_course_metadata.py``. Skips when
Postgres is unreachable.
"""

import os
import uuid

import pytest
import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import Ltree

from computor_backend.business_logic import course_deployment
from computor_backend.exceptions import BadRequestException
from computor_backend.model.course import (
    Course,
    CourseContent,
    CourseContentKind,
    CourseContentType,
    CourseFamily,
)
from computor_backend.model.language import Language
from computor_backend.model.organization import Organization
from computor_backend.permissions.principal import Principal
from computor_types.deployment_config import HierarchicalCourseConfig


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
def family(db, monkeypatch):
    monkeypatch.setattr(course_deployment, "get_cache", lambda: None)
    # The CI schema comes from create_all, without the migrations' seed rows.
    for kind, submittable in (("unit", False), ("assignment", True)):
        if db.get(CourseContentKind, kind) is None:
            db.add(CourseContentKind(id=kind, title=kind.title(), has_ascendants=True,
                                     has_descendants=not submittable, submittable=submittable))
    if db.get(Language, "de") is None:
        db.add(Language(code="de", name="German"))
    db.flush()
    suffix = uuid.uuid4().hex[:10]
    org = Organization(title="Deploy Org", organization_type="organization",
                       path=Ltree(f"deploy_{suffix}"), properties={})
    db.add(org)
    db.flush()
    fam = CourseFamily(title="Deploy Family", path=Ltree(f"deploy_{suffix}.family"),
                       organization_id=org.id)
    db.add(fam)
    db.flush()
    return fam


_COURSE_YAML = """
name: Data Science – Grundlagen
path: ds_grundlagen
description: Einstieg
content_types:
  - slug: weekly
    kind: unit
    title: Woche
    description: Eine Woche
contents:
  - path: week_1
    content_type: weekly
    title: Woche 1
    description: Erste Schritte
"""


def _deploy(db, family, document):
    config = HierarchicalCourseConfig(**document)
    result = course_deployment.deploy_course_from_config(
        db, Principal(is_admin=True), family.id, config
    )
    course = db.get(Course, result.course_id)
    (content_type,) = db.query(CourseContentType).filter(CourseContentType.course_id == course.id)
    (content,) = db.query(CourseContent).filter(CourseContent.course_id == course.id)
    return course, content_type, content


def _columns(row, *names):
    return {name: getattr(row, name) for name in names}


@pytest.mark.integration
def test_a_course_file_without_the_new_keys_deploys_as_before(db, family):
    course, content_type, content = _deploy(db, family, yaml.safe_load(_COURSE_YAML))

    assert _columns(course, "title", "description", "title_i18n", "description_i18n") == {
        "title": "Data Science – Grundlagen", "description": "Einstieg",
        "title_i18n": None, "description_i18n": None,
    }
    # Unset by the file; whatever the database fills in, as before.
    assert course.language_code in (None, "en")
    assert _columns(content_type, "title", "description", "title_i18n", "description_i18n") == {
        "title": "Woche", "description": "Eine Woche", "title_i18n": None, "description_i18n": None,
    }
    assert _columns(content, "title", "description", "title_i18n", "description_i18n") == {
        "title": "Woche 1", "description": "Erste Schritte", "title_i18n": None, "description_i18n": None,
    }


@pytest.mark.integration
def test_a_course_file_with_maps_stores_them(db, family):
    document = yaml.safe_load(_COURSE_YAML)
    document.update(language_code="de",
                    title_i18n={"en": "Data Science – Foundations"},
                    description_i18n={"en": "Getting started"})
    document["content_types"][0]["title_i18n"] = {"en": "Week"}
    document["contents"][0]["title_i18n"] = {"de": "Woche 1", "en": "Week 1"}
    document["contents"][0]["description_i18n"] = {"en": "First steps"}

    course, content_type, content = _deploy(db, family, document)

    assert course.title == "Data Science – Grundlagen"  # source text unchanged
    assert course.language_code == "de"
    assert course.title_i18n == {"en": "Data Science – Foundations"}
    assert course.description_i18n == {"en": "Getting started"}
    assert content_type.title_i18n == {"en": "Week"}
    assert content.title_i18n == {"de": "Woche 1", "en": "Week 1"}
    assert content.description_i18n == {"en": "First steps"}


@pytest.mark.integration
def test_an_unknown_language_code_is_rejected_before_anything_is_written(db, family):
    document = {**yaml.safe_load(_COURSE_YAML), "language_code": "xx"}

    with pytest.raises(BadRequestException, match="language_code 'xx'"):
        _deploy(db, family, document)
    assert db.query(Course).filter(Course.course_family_id == family.id).count() == 0
