from pydantic import BaseModel, field_validator, ConfigDict
from typing import Optional
    
from computor_types.base import EntityInterface, ListQuery
from computor_types.course_content_types import CourseContentTypeGet

class CourseStudentRepository(BaseModel):
    provider_url: Optional[str] = None
    full_path: Optional[str] = None

class CourseStudentGet(BaseModel):
    id: str
    title: Optional[str] = None
    course_family_id: Optional[str] = None
    organization_id: Optional[str] = None
    course_content_types: list[CourseContentTypeGet]
    path: str

    # Optional: a course may have no git binding exposed to the student (e.g. courses
    # using the managed Forgejo binding rather than legacy `properties.gitlab`).
    repository: Optional[CourseStudentRepository] = None

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

    # Optional: see CourseStudentGet.repository.
    repository: Optional[CourseStudentRepository] = None

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
    provider_url: Optional[str] = None
    full_path: Optional[str] = None
    full_path_student: Optional[str] = None

class CourseStudentInterface(EntityInterface):
    list = CourseStudentList
    query = CourseStudentQuery
