from pydantic import BaseModel, ConfigDict
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from computor_types.base import EntityInterface, ListQuery

class CourseRoleGet(BaseModel):
    id: str
    title: Optional[str] = None
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class CourseRoleList(CourseRoleGet):
    id: str
    title: Optional[str] = None
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
    
class CourseRoleQuery(ListQuery):
    id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None

def course_role_search(db: 'Session', query, params: Optional[CourseRoleQuery]):
    if params.id != None:
        query = query.filter(id == params.id)
    if params.title != None:
        query = query.filter(title == params.title)
    if params.description != None:
        query = query.filter(description == params.description)
    return query

class CourseRoleInterface(EntityInterface):
    create = None
    get = CourseRoleGet
    list = CourseRoleList
    update = None
    query = CourseRoleQuery
    search = course_role_search
    endpoint = "course-roles"
    model = None  # Set by backend
    cache_ttl=600