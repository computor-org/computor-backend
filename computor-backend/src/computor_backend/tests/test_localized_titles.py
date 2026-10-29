"""Per-language titles and descriptions (computor-org/issues#550).

``title``/``description`` stay the source text; ``title_i18n`` and
``description_i18n`` carry other languages, and only a client that sends
``?localize=<de|en>`` gets them in place of the source text. DB-free: the
student view repository and the catalog query are replaced by fakes.
"""
from types import SimpleNamespace

import pytest
import yaml
from fastapi.testclient import TestClient

from computor_backend.api import public_catalog
from computor_backend.api.examples import _split_promoted_meta
from computor_backend.business_logic import students as students_bl
from computor_backend.business_logic.localization import (
    i18n_map,
    localize,
    localize_dto,
    localized_text,
)
from computor_types.course_content_types import CourseContentTypeList
from computor_types.courses import CoursePublicCatalogEntry
from computor_types.deployment_config import HierarchicalCourseConfig
from computor_types.student_course_contents import CourseContentStudentList

TITLES = {"de": "Woche 1", "en": "Week 1"}


@pytest.mark.parametrize(
    "lang, mapping, expected",
    [
        ("de", TITLES, "Woche 1"),
        ("en", TITLES, "Week 1"),
        ("en", {"de": "Woche 1"}, "Quelle"),  # no entry for the language
        ("en", {"en": ""}, "Quelle"),  # an empty entry is no translation
        ("en", {"en": "   "}, "Quelle"),
        ("en", None, "Quelle"),  # content without maps
        (None, TITLES, "Quelle"),  # client did not ask
        ("fr", TITLES, "Quelle"),
    ],
)
def test_localized_text(lang, mapping, expected):
    assert localized_text(mapping, lang, "Quelle") == expected


def test_localize_resolves_title_and_description_independently():
    obj = SimpleNamespace(title="Woche 1", description="Grundlagen",
                          title_i18n={"en": "Week 1"}, description_i18n=None)
    assert localize(obj, "en") == ("Week 1", "Grundlagen")


@pytest.mark.parametrize(
    "value, expected",
    [
        ({"de": "Woche", "en": "Week"}, {"de": "Woche", "en": "Week"}),
        ({"de": "Woche", "en": None, "fr": 3}, {"de": "Woche"}),
        ({}, None),
        ("Week", None),
        (None, None),
    ],
)
def test_i18n_map_keeps_only_text(value, expected):
    assert i18n_map(value) == expected


def _row(**overrides):
    data = dict(
        id="cc-1", title="Woche 1", description="Grundlagen", path="week_1",
        course_id="c-1", course_content_type_id="ct-1", course_content_kind_id="unit",
        position=1.0, max_group_size=1, submitted=False, result_count=0, submission_count=0,
        color="green",
        course_content_type=CourseContentTypeList(id="ct-1", slug="weekly", color="green",
                                                  course_id="c-1", course_content_kind_id="unit"),
        title_i18n={"de": "Woche 1", "en": "Week 1"},
        description_i18n={"en": "Basics"},
    )
    data.update(overrides)
    return CourseContentStudentList(**data)


def test_localize_dto_without_lang_returns_the_same_object():
    row = _row()
    assert localize_dto(row, None) is row


def test_localize_dto_does_not_touch_the_cached_instance():
    row = _row()
    localized = localize_dto(row, "en")
    assert (localized.title, localized.description) == ("Week 1", "Basics")
    assert (row.title, row.description) == ("Woche 1", "Grundlagen")
    assert localized.title_i18n == row.title_i18n


# --- Student endpoints, through the real routes ---------------------------


class _FakeRepo:
    rows = [_row()]

    def __init__(self, cache=None, user_id=None):
        pass

    async def list_course_contents(self, user_id, params, permissions):
        return self.rows

    async def get_course_content(self, user_id, course_content_id, permissions):
        return self.rows[0]

    def close(self):
        pass


@pytest.fixture
def student_client(monkeypatch):
    from computor_backend.permissions.auth import get_current_principal
    from computor_backend.permissions.principal import Principal
    from computor_backend.redis_cache import get_cache
    from computor_backend.server import app

    monkeypatch.setattr(students_bl, "StudentViewRepository", _FakeRepo)
    app.dependency_overrides[get_current_principal] = lambda: Principal(user_id="u-1")
    app.dependency_overrides[get_cache] = lambda: None
    try:
        yield TestClient(app)  # no `with`: lifespan (Temporal, Coder, ...) not started
    finally:
        app.dependency_overrides.pop(get_current_principal, None)
        app.dependency_overrides.pop(get_cache, None)


def test_student_contents_keep_the_source_text_without_localize(student_client):
    (row,) = student_client.get("/students/course-contents").json()
    assert (row["title"], row["description"]) == ("Woche 1", "Grundlagen")
    assert row["title_i18n"] == {"de": "Woche 1", "en": "Week 1"}


def test_student_contents_with_localize_en(student_client):
    (row,) = student_client.get("/students/course-contents?localize=en").json()
    assert (row["title"], row["description"]) == ("Week 1", "Basics")
    assert row["title_i18n"] == {"de": "Woche 1", "en": "Week 1"}


def test_student_content_get_with_localize_en(student_client, monkeypatch):
    from computor_types.student_course_contents import CourseContentStudentGet

    detail = CourseContentStudentGet(
        **_row().model_dump(exclude={"course_content_type"}),
        course_content_type=dict(id="ct-1", slug="weekly", color="green", course_id="c-1",
                                 course_content_kind_id="unit"),
    )
    monkeypatch.setattr(_FakeRepo, "rows", [detail])
    body = student_client.get("/students/course-contents/cc-1?localize=en").json()
    assert body["title"] == "Week 1"
    assert student_client.get("/students/course-contents/cc-1").json()["title"] == "Woche 1"


# --- Anonymous catalog, through the real route ----------------------------


def test_public_catalog_localizes_after_the_cache(monkeypatch):
    from contextlib import nullcontext

    from computor_backend.server import app

    entry = CoursePublicCatalogEntry(id="c-1", title="Grundlagen", description="Einstieg",
                                     title_i18n={"en": "Foundations"})
    monkeypatch.setattr(public_catalog, "list_anonymous_catalog", lambda db: [entry])
    monkeypatch.setattr(public_catalog, "_session_factory", nullcontext)
    public_catalog.clear_public_catalog_cache()
    try:
        client = TestClient(app)
        (english,) = client.get("/public/courses?localize=en").json()
        (plain,) = client.get("/public/courses").json()
    finally:
        public_catalog.clear_public_catalog_cache()

    assert (english["title"], english["description"]) == ("Foundations", "Einstieg")
    # Same snapshot, served afterwards without the parameter: untouched.
    assert plain == {"id": "c-1", "title": "Grundlagen", "description": "Einstieg",
                     "title_i18n": {"en": "Foundations"}, "description_i18n": None,
                     "language_code": None, "position": None}


# --- Course files and meta.yaml -------------------------------------------

_COURSE_YAML = """
name: Data Science – Grundlagen
path: ds_grundlagen
description: Einstieg
content_types:
  - slug: weekly
    kind: unit
    title: Woche
contents:
  - path: week_1
    content_type: weekly
    title: Woche 1
"""

_I18N_YAML = _COURSE_YAML.replace(
    "description: Einstieg\n",
    "description: Einstieg\nlanguage_code: de\n"
    "title_i18n: {en: Data Science – Foundations}\n"
    "description_i18n: {en: Getting started}\n",
).replace(
    "    title: Woche 1\n",
    "    title: Woche 1\n    title_i18n: {en: Week 1}\n",
).replace(
    "    title: Woche\n",
    "    title: Woche\n    title_i18n: {en: Week}\n",
)


def test_course_file_without_maps_parses_as_before():
    config = HierarchicalCourseConfig(**yaml.safe_load(_COURSE_YAML))
    assert config.title_i18n is None and config.description_i18n is None
    assert config.language_code is None
    assert config.content_types[0].title_i18n is None
    assert config.contents[0].title_i18n is None


def test_course_file_with_maps_and_language_code():
    config = HierarchicalCourseConfig(**yaml.safe_load(_I18N_YAML))
    assert config.title_i18n == {"en": "Data Science – Foundations"}
    assert config.description_i18n == {"en": "Getting started"}
    assert config.language_code == "de"
    assert config.content_types[0].title_i18n == {"en": "Week"}
    assert config.contents[0].title_i18n == {"en": "Week 1"}


def test_course_language_code_must_be_a_two_letter_code():
    with pytest.raises(ValueError):
        HierarchicalCourseConfig(**{**yaml.safe_load(_COURSE_YAML), "language_code": "python"})


def test_meta_yaml_maps_reach_the_example_version_columns():
    promoted = _split_promoted_meta({"title": "Wurfparabel",
                                     "title_i18n": {"en": "Projectile motion"},
                                     "language": "de"})
    assert promoted["title_i18n"] == {"en": "Projectile motion"}
    assert promoted["description_i18n"] is None
    # meta.yaml `language` is the content language and keeps its own column.
    assert promoted["language"] == "de"
    assert _split_promoted_meta({"title": "Wurfparabel"})["title_i18n"] is None


# --- The student view mapper carries the maps from the row ----------------


class _NoPrefetch:
    def latest_artifact_id(self, submission_group):
        return None

    def latest_grade(self, artifact_id):
        return None


@pytest.mark.asyncio
async def test_student_view_mapper_carries_the_maps():
    from computor_backend.repositories.view_mappers import (
        course_member_course_content_result_mapper,
    )

    content_type = SimpleNamespace(id="ct-1", slug="weekly", title="Woche", title_i18n={"en": "Week"},
                                   color="green", course_id="c-1", course_content_kind_id="unit",
                                   course_content_kind=None)
    content = SimpleNamespace(
        id="cc-1", title="Woche 1", description="Grundlagen", path="week_1", course_id="c-1",
        course_content_type_id="ct-1", course_content_kind_id="unit", position=1.0,
        max_group_size=1, max_test_runs=None, max_submissions=None, testing_service_id=None,
        is_submittable=False, deployment=None, course_content_type=content_type,
        course=SimpleNamespace(max_test_runs=None, max_submissions=None),
        title_i18n={"en": "Week 1"}, description_i18n={"en": "Basics"},
    )
    qr = SimpleNamespace(
        course_content=content, submission_group=None, submission_group_unread_count=0,
        result=None, submission_grading=None, submission_status_int=None,
        latest_grade_status_int=None, submission_count=0, result_count=0, is_latest_unreviewed=0,
    )

    dto = await course_member_course_content_result_mapper(qr, db=None, prefetch=_NoPrefetch())

    assert (dto.title, dto.title_i18n, dto.description_i18n) == ("Woche 1", {"en": "Week 1"}, {"en": "Basics"})
    assert dto.course_content_type.title_i18n == {"en": "Week"}


# --- Lecturer and tutor views, through the real routes ---------------------

_CONTENT_ROW = dict(
    id="cc-1", title="Woche 1", description="Grundlagen", path="week_1", course_id="c-1",
    course_content_type_id="ct-1", course_content_kind_id="unit", position=1.0,
    title_i18n={"de": "Woche 1", "en": "Week 1"}, description_i18n={"en": "Basics"},
    repository={"url": None, "full_path": None},
)


class _FakeLecturerRepo:
    """Builds rows the way ``LecturerViewRepository`` does: from the ORM ``__dict__``."""

    def __init__(self, cache=None, user_id=None):
        pass

    def list_course_contents(self, permissions, params):
        from computor_types.lecturer_course_contents import CourseContentLecturerList
        return [CourseContentLecturerList.model_validate(dict(_CONTENT_ROW))]

    def get_course_content(self, course_content_id, permissions):
        from computor_types.lecturer_course_contents import CourseContentLecturerGet
        return CourseContentLecturerGet.model_validate(dict(_CONTENT_ROW))

    def close(self):
        pass


_COURSE = SimpleNamespace(
    id="c-1", title="Grundlagen", description="Einstieg", position=1.0,
    title_i18n={"en": "Foundations"}, description_i18n={"en": "Getting started"},
    course_family_id="f-1", organization_id="o-1", path="ds", properties={},
)


@pytest.fixture
def staff_client(monkeypatch):
    from computor_backend.business_logic import lecturer as lecturer_bl
    from computor_backend.permissions.auth import get_current_principal
    from computor_backend.permissions.principal import Principal
    from computor_backend.redis_cache import get_cache
    from computor_backend.repositories.tutor_view import TutorViewRepository
    from computor_backend.server import app

    monkeypatch.setattr(lecturer_bl, "LecturerViewRepository", _FakeLecturerRepo)
    # The real tutor row builders, fed one course instead of a permission query.
    monkeypatch.setattr(TutorViewRepository, "_list_cached_course_dtos",
                        lambda self, permissions, params, *, row_builder, **kw: [row_builder(_COURSE)])
    monkeypatch.setattr(TutorViewRepository, "_get_cached_course_dto",
                        lambda self, course_id, permissions, *, builder, **kw: builder(_COURSE)[0])
    app.dependency_overrides[get_current_principal] = lambda: Principal(user_id="u-1")
    app.dependency_overrides[get_cache] = lambda: None
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_current_principal, None)
        app.dependency_overrides.pop(get_cache, None)


@pytest.mark.parametrize("url", ["/lecturers/course-contents", "/lecturers/course-contents/cc-1"])
def test_lecturer_contents_carry_the_maps(staff_client, url):
    body = staff_client.get(url).json()
    row = body[0] if isinstance(body, list) else body
    assert (row["title"], row["description"]) == ("Woche 1", "Grundlagen")
    assert row["title_i18n"] == {"de": "Woche 1", "en": "Week 1"}
    assert row["description_i18n"] == {"en": "Basics"}

    body = staff_client.get(url + "?localize=en").json()
    row = body[0] if isinstance(body, list) else body
    assert (row["title"], row["description"]) == ("Week 1", "Basics")


@pytest.mark.parametrize("url", ["/tutors/courses", "/tutors/courses/c-1"])
def test_tutor_courses_carry_the_maps(staff_client, url):
    body = staff_client.get(url).json()
    course = body[0] if isinstance(body, list) else body
    assert (course["title"], course["description"]) == ("Grundlagen", "Einstieg")
    assert course["title_i18n"] == {"en": "Foundations"}
    assert course["description_i18n"] == {"en": "Getting started"}

    body = staff_client.get(url + "?localize=en").json()
    course = body[0] if isinstance(body, list) else body
    assert (course["title"], course["description"]) == ("Foundations", "Getting started")


def test_localize_as_accepts_a_cached_dict():
    # Tutor content views return the cached dict as is on a cache hit.
    from computor_backend.business_logic.localization import localize_as

    cached = _row().model_dump()
    localized = localize_as(cached, CourseContentStudentList, "en")
    assert (localized.title, localized.description) == ("Week 1", "Basics")
    assert localize_as(cached, CourseContentStudentList, None) is cached
