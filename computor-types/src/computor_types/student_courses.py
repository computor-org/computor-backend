from pydantic import BaseModel, field_validator, ConfigDict
from typing import Optional

from computor_types.base import EntityInterface, ListQuery
from computor_types.course_content_types import CourseContentTypeGet

# NOTE: A course's git repository is no longer exposed on these DTOs. Git moved
# from the org level to the course level and is lazy/per-student (Forgejo babysat,
# GitLab BYO, or none). Student repo state is served by the dedicated course-git
# endpoints (GET /user/.../course-git-descriptor, /student-repository) using the
# computor_types.course_git DTOs — that is the single source of truth.


class CourseStudentGet(BaseModel):
    id: str
    title: Optional[str] = None
    course_family_id: Optional[str] = None
    organization_id: Optional[str] = None
    course_content_types: list[CourseContentTypeGet]
    path: str

    model_config = ConfigDict(from_attributes=True)

    @field_validator('path', mode='before')
    @classmethod
    def cast_str_to_ltree(cls, value):
        return str(value)


class CourseStudentList(BaseModel):
    id: str
    title: Optional[str] = None
    course_family_id: Optional[str] = None
    organization_id: Optional[str] = None
    path: str

    model_config = ConfigDict(from_attributes=True)

    @field_validator('path', mode='before')
    @classmethod
    def cast_str_to_ltree(cls, value):
        return str(value)


class CourseStudentQuery(ListQuery):
    id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    path: Optional[str] = None
    course_family_id: Optional[str] = None
    organization_id: Optional[str] = None


class CourseStudentInterface(EntityInterface):
    list = CourseStudentList
    query = CourseStudentQuery
