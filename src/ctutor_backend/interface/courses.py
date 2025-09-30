from pydantic import BaseModel, field_validator, ConfigDict
from typing import Optional
from sqlalchemy.orm import Session
from ctutor_backend.interface.course_families import CourseFamilyGet
from ctutor_backend.interface.deployments import GitLabConfig, GitLabConfigGet
from ctutor_backend.interface.base import BaseEntityGet, EntityInterface, ListQuery
from ctutor_backend.model.course import Course
from ..custom_types import Ltree

class CourseProperties(BaseModel):
    gitlab: Optional[GitLabConfig] = None
    
    model_config = ConfigDict(
        extra='allow',
    )

class CoursePropertiesGet(BaseModel):
    gitlab: Optional[GitLabConfigGet] = None
    
    model_config = ConfigDict(
        extra='allow',
    )
    
class CourseCreate(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    path: str
    course_family_id: str
    language_code: Optional[str] = None
    properties: Optional[CourseProperties] = None

class CourseGet(BaseEntityGet,CourseCreate):
    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    path: str
    course_family_id: str
    organization_id: str
    language_code: Optional[str] = None
    properties: Optional[CoursePropertiesGet] = None

    course_family: Optional[CourseFamilyGet] = None

    @field_validator('path', mode='before')
    @classmethod
    def cast_str_to_ltree(cls, value):
        return str(value)
    
    model_config = ConfigDict(from_attributes=True)

class CourseList(BaseModel):
    id: str
    title: Optional[str] = None
    course_family_id: Optional[str] = None
    organization_id: Optional[str] = None
    path: str
    language_code: Optional[str] = None
    properties: Optional[CoursePropertiesGet] = None

    @field_validator('path', mode='before')
    @classmethod
    def cast_str_to_ltree(cls, value):
        return str(value)

    model_config = ConfigDict(from_attributes=True)

class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    language_code: Optional[str] = None
    properties: Optional[CourseProperties] = None

class CourseQuery(ListQuery):
    id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    path: Optional[str] = None
    course_family_id: Optional[str] = None
    organization_id: Optional[str] = None
    provider_url: Optional[str] = None
    full_path: Optional[str] = None

def course_search(db: Session, query, params: Optional[CourseQuery]):
    if params.id != None:
        query = query.filter(Course.id == params.id)
    if params.title != None:
        query = query.filter(Course.title == params.title)
    if params.description != None:
        query = query.filter(Course.description == params.description)
    if params.path != None:
        query = query.filter(Course.path == Ltree(params.path))
    if params.course_family_id != None:
        query = query.filter(Course.course_family_id == params.course_family_id)
    if params.organization_id != None:
        query = query.filter(Course.organization_id == params.organization_id)
    if params.provider_url != None:
         query = query.filter(Course.properties["gitlab"].op("->>")("url") == params.provider_url)
    if params.full_path != None:
        query = query.filter(Course.properties["gitlab"].op("->>")("full_path") == params.full_path)
    return query

class CourseInterface(EntityInterface):
    create = CourseCreate
    get = CourseGet
    list = CourseList
    update = CourseUpdate
    query = CourseQuery
    search = course_search
    endpoint = "courses"
    model = Course
    cache_ttl = 300  # 5 minutes - course data changes moderately frequently