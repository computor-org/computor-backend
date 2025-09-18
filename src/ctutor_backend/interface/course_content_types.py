from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional
from sqlalchemy.orm import Session
from ctutor_backend.interface.base import BaseEntityGet, EntityInterface, ListQuery
from ctutor_backend.interface.course_content_kind import CourseContentKindGet, CourseContentKindList
from ctutor_backend.model.course import CourseContentType
from ctutor_backend.utils.color_validation import is_valid_color, validate_color

class CourseContentTypeCreate(BaseModel):
    slug: str
    title: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = 'green'
    properties: Optional[dict] = None
    course_id: str
    course_content_kind_id: str

    model_config = ConfigDict(from_attributes=True)
    
    @field_validator('color')
    @classmethod
    def validate_color_field(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        
        normalized_color = validate_color(v)
        if normalized_color is None:
            raise ValueError(f'Invalid color format: {v}. Must be a valid HTML/CSS color (hex, rgb, hsl, or named color)')
        
        return normalized_color

class CourseContentTypeGet(BaseEntityGet):
    id: str 
    slug: str
    title: Optional[str] = None
    description: Optional[str] = None
    color: str
    properties: Optional[dict] = None
    course_id: str
    course_content_kind_id: str

    course_content_kind: Optional[CourseContentKindGet] = None

    model_config = ConfigDict(from_attributes=True)

class CourseContentTypeList(BaseModel):
    id: str
    slug: str
    title: Optional[str] = None
    color: str
    course_id: str
    course_content_kind_id: str

    course_content_kind: Optional[CourseContentKindList] = None

    model_config = ConfigDict(from_attributes=True)

class CourseContentTypeUpdate(BaseModel):
    slug: Optional[str] = None
    title: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None
    properties: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)
    
    @field_validator('color')
    @classmethod
    def validate_color_field(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        
        normalized_color = validate_color(v)
        if normalized_color is None:
            raise ValueError(f'Invalid color format: {v}. Must be a valid HTML/CSS color (hex, rgb, hsl, or named color)')
        
        return normalized_color

class CourseContentTypeQuery(ListQuery):
    id: Optional[str] = None
    slug: Optional[str] = None
    title: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None
    course_id: Optional[str] = None
    properties: Optional[str] = None
    course_content_kind_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

def course_content_type_search(db: Session, query, params: Optional[CourseContentTypeQuery]):
    if params.id != None:
        query = query.filter(CourseContentType.id == params.id)
    if params.slug != None:
        query = query.filter(CourseContentType.slug == params.slug)
    if params.title != None:
        query = query.filter(CourseContentType.title == params.title)
    if params.color != None:
        query = query.filter(CourseContentType.color == params.color)
    if params.course_id != None:
        query = query.filter(CourseContentType.course_id == params.course_id)
    if params.course_content_kind_id != None:
        query = query.filter(CourseContentType.course_content_kind_id == params.course_content_kind_id)

    return query

class CourseContentTypeInterface(EntityInterface):
    create = CourseContentTypeCreate
    get = CourseContentTypeGet
    list = CourseContentTypeList
    update = CourseContentTypeUpdate
    query = CourseContentTypeQuery
    search = course_content_type_search
    endpoint = "course-content-types"
    model = CourseContentType
    cache_ttl=60