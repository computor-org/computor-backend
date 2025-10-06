from pydantic import BaseModel, ConfigDict
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from computor_types.base import BaseEntityGet, EntityInterface, ListQuery

class CourseGroupCreate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    course_id: str
    properties: Optional[dict] = None

class CourseGroupGet(BaseEntityGet,CourseGroupCreate):
    id: str

    model_config = ConfigDict(from_attributes=True)
class CourseGroupList(BaseModel):
    id: str
    title: Optional[str] = None
    course_id: str

    model_config = ConfigDict(from_attributes=True)
    
class CourseGroupUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    course_id: Optional[str] = None
    properties: Optional[dict] = None

class CourseGroupQuery(ListQuery):
    id: Optional[str] = None
    title: Optional[str] = None
    course_id: Optional[str] = None
    properties: Optional[str] = None
    
def course_group_search(db: 'Session', query, params: Optional[CourseGroupQuery]):
    if params.id != None:
        query = query.filter(id == params.id)
    if params.title != None:
        query = query.filter(title == params.title)
    if params.course_id != None:
        query = query.filter(course_id == params.course_id)

    return query.order_by(CourseGroup.title)

class CourseGroupInterface(EntityInterface):
    create = CourseGroupCreate
    get = CourseGroupGet
    list = CourseGroupList
    update = CourseGroupUpdate
    query = CourseGroupQuery
    search = course_group_search
    endpoint = "course-groups"
    model = None  # Set by backend
    cache_ttl=60