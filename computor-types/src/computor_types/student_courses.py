from pydantic import BaseModel, field_validator, ConfigDict
from typing import Optional


    
from computor_types.base import EntityInterface, ListQuery
from computor_types.course_content_types import CourseContentTypeGet, CourseContentTypeList

from computor_types.custom_types import Ltree

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

    repository: CourseStudentRepository

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

    repository: CourseStudentRepository

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

# BACKEND FUNCTION - Moved to backend in Phase 4
# def course_student_search(db: 'Session', query, params: Optional[CourseStudentQuery]):
#     if params.id != None:
#         query = query.filter(id == params.id)
#     if params.title != None:
#         query = query.filter(title == params.title)
#     if params.description != None:
#         query = query.filter(description == params.description)
#     if params.path != None:
#         query = query.filter(path == Ltree(params.path))
#     if params.course_family_id != None:
#         query = query.filter(course_family_id == params.course_family_id)
#     if params.organization_id != None:
#         query = query.filter(organization_id == params.organization_id)
#
#     if params.provider_url != None:
#         query = query.filter(properties["gitlab"].op("->>")("url") == params.provider_url)
#     if params.full_path != None:
#         query = query.filter(properties["gitlab"].op("->>")("full_path") == params.full_path)
#     if params.full_path_student != None:
#         query = query.join(CourseMember,CourseMember.course_id == Course.id).filter(properties["gitlab"].op("->>")("full_path") == params.full_path_student)
#
#     return query
#
class CourseStudentInterface(EntityInterface):
    list = CourseStudentList
    query = CourseStudentQuery
