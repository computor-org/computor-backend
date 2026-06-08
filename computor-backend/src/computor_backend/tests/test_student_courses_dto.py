"""Regression tests for the student-courses DTOs.

`GET /students/courses` 500'd because `CourseStudentList.repository` was required
while `list_courses` passes `repository=None` for courses with no legacy
`properties.gitlab` (now the norm under the Forgejo git binding). The field is
optional; these tests pin that.
"""

from computor_types.student_courses import (
    CourseStudentList,
    CourseStudentGet,
    CourseStudentRepository,
)


def test_course_student_list_allows_null_repository():
    item = CourseStudentList(id="c1", path="org.fam.course", repository=None)
    assert item.repository is None


def test_course_student_list_defaults_repository_to_none():
    item = CourseStudentList(id="c1", path="org.fam.course")
    assert item.repository is None


def test_course_student_list_accepts_a_repository():
    repo = CourseStudentRepository(provider_url="https://git.example", full_path="org/course")
    item = CourseStudentList(id="c1", path="org.fam.course", repository=repo)
    assert item.repository.full_path == "org/course"


def test_course_student_get_allows_null_repository():
    item = CourseStudentGet(id="c1", path="org.fam.course", course_content_types=[], repository=None)
    assert item.repository is None
