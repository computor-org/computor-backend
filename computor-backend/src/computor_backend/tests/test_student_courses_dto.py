"""Tests for the student-courses DTOs after dropping the legacy git repository field.

`GET /students/courses` used to 500 because `CourseStudentList.repository` was a
required field fed from the legacy `properties.gitlab`, which is empty now that git
moved to the course level (Forgejo babysat / GitLab BYO / none). The repository
field was removed; student repo state is served by the dedicated course-git
descriptor endpoints (computor_types.course_git). These tests pin the new shape.
"""

import pytest

from computor_types.student_courses import (
    CourseStudentList,
    CourseStudentGet,
    CourseStudentQuery,
)


def test_course_student_list_has_no_repository_field():
    item = CourseStudentList(id="c1", path="org.fam.course")
    assert not hasattr(item, "repository")


def test_course_student_get_has_no_repository_field():
    item = CourseStudentGet(id="c1", path="org.fam.course", course_content_types=[])
    assert not hasattr(item, "repository")


def test_course_student_list_constructs_from_minimal_fields():
    item = CourseStudentList(
        id="c1",
        title="Intro",
        course_family_id="f1",
        organization_id="o1",
        path="org.fam.course",
    )
    assert item.path == "org.fam.course"
    assert item.title == "Intro"


def test_query_drops_legacy_gitlab_filters():
    fields = CourseStudentQuery.model_fields
    for legacy in ("provider_url", "full_path", "full_path_student"):
        assert legacy not in fields


def test_course_student_repository_dto_is_gone():
    import computor_types.student_courses as sc
    assert not hasattr(sc, "CourseStudentRepository")


def test_student_course_search_only_touches_existing_query_fields():
    """Guards the regression where search() referenced removed legacy params
    (params.provider_url / full_path / full_path_student) -> AttributeError 500."""
    from unittest.mock import MagicMock
    from computor_backend.interfaces.student_courses import CourseStudentInterface

    params = CourseStudentQuery(
        id=None, title="Algorithms", description=None,
        path="org.fam.course", course_family_id=None, organization_id=None,
    )
    query = MagicMock()
    # Must not raise AttributeError for fields that no longer exist on the DTO.
    result = CourseStudentInterface.search(MagicMock(), query, params)
    assert result is not None
