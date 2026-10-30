"""A content release with new example versions reaches a course that is already deployed.

``sync_course_metadata`` ships the new instructions, but each assignment kept
the example version it was first released with, so learners read about names
the tests do not check. ``sync_example_versions`` reports every assignment whose
deployed version differs from the release's meta.yaml, and refuses anything
that is not a plain version move.

Runs against a live Postgres inside a rolled-back transaction, like
``test_sync_course_metadata.py``. Skips when Postgres is unreachable.
"""

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import Ltree

from computor_backend.model.course import (
    Course,
    CourseContent,
    CourseContentKind,
    CourseContentType,
    CourseFamily,
)
from computor_backend.model.deployment import CourseContentDeployment
from computor_backend.model.example import Example, ExampleRepository, ExampleVersion
from computor_backend.model.organization import Organization
from computor_backend.scripts.sync_example_versions import (
    check_course,
    package_examples,
    release_versions,
)


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


RELEASED = datetime(2026, 10, 1, tzinfo=timezone.utc)


@pytest.fixture
def deployed(db):
    """A released course: forsum 1.0.2, gauss 1.0.1 and caesar 1.0.4, all deployed."""
    for kind, submittable in (("unit", False), ("assignment", True)):
        if db.get(CourseContentKind, kind) is None:
            db.add(CourseContentKind(id=kind, title=kind.title(), has_ascendants=True,
                                     has_descendants=not submittable, submittable=submittable))
    db.flush()
    suffix = uuid.uuid4().hex[:10]
    org = Organization(title="Versions Org", organization_type="organization",
                       path=Ltree(f"ver_{suffix}"), properties={})
    db.add(org)
    db.flush()
    family = CourseFamily(title="Versions Family", path=Ltree(f"ver_{suffix}.family"),
                          organization_id=org.id)
    db.add(family)
    db.flush()
    course = Course(title="Grundlagen", path=Ltree(f"ver_{suffix}.beginner"),
                    course_family_id=family.id, organization_id=org.id)
    db.add(course)
    db.flush()
    weekly = CourseContentType(slug="weekly", title="Woche", color="green",
                               course_content_kind_id="unit", course_id=course.id)
    task = CourseContentType(slug="task", title="Aufgabe", color="yellow",
                             course_content_kind_id="assignment", course_id=course.id)
    db.add_all([weekly, task])
    db.flush()
    repo = ExampleRepository(name="Versions Repo", source_type="minio",
                             source_url=f"versions-{suffix}", organization_id=org.id)
    db.add(repo)
    db.flush()
    db.add(CourseContent(title="Woche 1", path=Ltree("week_1"), course_id=course.id,
                         course_content_type_id=weekly.id, position=1.0, max_group_size=1))
    for name, version in (("forsum", "1.0.2"), ("gauss", "1.0.1"), ("caesar", "1.0.4")):
        identifier = f"ver_{suffix}.{name}"
        example = Example(example_repository_id=repo.id, directory=identifier,
                          identifier=Ltree(identifier), title=name)
        db.add(example)
        db.flush()
        ev = ExampleVersion(example_id=example.id, version_tag=version, version_number=1,
                            storage_path=f"versions-{suffix}/{name}/v1")
        content = CourseContent(title=name, path=Ltree(f"week_1.{name}"), course_id=course.id,
                                course_content_type_id=task.id, course_content_kind_id="assignment",
                                position=1.0, max_group_size=1, is_submittable=True)
        db.add_all([ev, content])
        db.flush()
        db.add(CourseContentDeployment(
            course_content_id=content.id, example_version_id=ev.id,
            example_identifier=Ltree(identifier), version_tag=version,
            deployment_status="deployed", assigned_at=RELEASED - timedelta(hours=1),
            deployed_at=RELEASED,
        ))
    db.flush()
    return course


def _config(course, names=("forsum", "gauss", "caesar")):
    prefix = str(course.path).split(".")[0]
    return {
        "path": str(course.path),
        "contents": [
            {"path": "week_1", "content_type": "weekly", "contents": [
                {"path": name, "content_type": "task", "example_identifier": f"{prefix}.{name}"}
                for name in names
            ]},
        ],
    }


def _wanted(course, **versions):
    prefix = str(course.path).split(".")[0]
    base = {"forsum": "1.0.5", "gauss": "1.0.1", "caesar": "1.0.4"}
    base.update(versions)
    return {f"{prefix}.{name}": v for name, v in base.items()}


def _deployment(db, course, name):
    content = db.query(CourseContent).filter(CourseContent.course_id == course.id,
                                             CourseContent.path == Ltree(f"week_1.{name}")).one()
    return content.deployment


@pytest.mark.integration
def test_reports_a_version_move_and_nothing_else(db, deployed):
    result = check_course(db, _config(deployed), _wanted(deployed))

    assert [(m.path, m.current, m.wanted) for m in result.moves] == [("week_1.forsum", "1.0.2", "1.0.5")]
    assert result.releases == [] and result.blocked == []


@pytest.mark.integration
def test_a_deployed_course_on_the_release_versions_is_clean(db, deployed):
    result = check_course(db, _config(deployed), _wanted(deployed, forsum="1.0.2"))

    assert result.moves == [] and result.releases == [] and result.blocked == []


@pytest.mark.integration
def test_an_assignment_not_released_since_its_move_is_released_again(db, deployed):
    d = _deployment(db, deployed, "forsum")
    d.version_tag = "1.0.5"
    d.deployment_status = "pending"
    d.assigned_at = RELEASED + timedelta(days=1)
    db.flush()

    result = check_course(db, _config(deployed), _wanted(deployed))

    assert [m.path for m in result.releases] == ["week_1.forsum"]
    assert result.moves == [] and result.blocked == []


@pytest.mark.integration
def test_refuses_what_is_not_a_version_move(db, deployed):
    gauss = _deployment(db, deployed, "gauss")
    gauss.deployed_at = None  # assigned, never released
    db.flush()
    config = _config(deployed, names=("forsum", "gauss", "caesar", "brand_new"))
    wanted = _wanted(deployed, caesar="1.0.3", brand_new="1.0.0")

    result = check_course(db, config, wanted)
    prefix = str(deployed.path).split(".")[0]

    assert [m.path for m in result.moves] == ["week_1.forsum"]
    assert result.blocked == [
        f"week_1.gauss: {prefix}.gauss was never released; needs a content release",
        f"week_1.caesar: deployed {prefix}.caesar 1.0.4 is newer than the release's 1.0.3",
        "week_1.brand_new: no deployed assignment; needs a content release",
    ]


@pytest.mark.integration
def test_refuses_a_move_the_examples_package_cannot_supply(db, deployed, tmp_path):
    prefix = str(deployed.path).split(".")[0]
    (tmp_path / "forsum").mkdir()
    (tmp_path / "forsum" / "meta.yaml").write_text(f"slug: {prefix}.forsum\nversion: '1.0.4'\n")

    result = check_course(db, _config(deployed), _wanted(deployed), package_examples(tmp_path))

    assert result.moves == []
    assert result.blocked == [
        f"week_1.forsum: the examples package has {prefix}.forsum 1.0.4, the release needs 1.0.5"
    ]


def test_release_versions_are_normalized_from_the_mirror(tmp_path):
    meta = tmp_path / "examples" / "python" / "x.forsum" / "meta.yaml"
    meta.parent.mkdir(parents=True)
    meta.write_text("slug: x.forsum\nversion: '1.1'\n")

    assert release_versions(tmp_path) == {"x.forsum": "1.1.0"}
