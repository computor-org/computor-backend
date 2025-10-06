from pydantic import BaseModel, ConfigDict
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from computor_types.base import BaseEntityGet, EntityInterface, ListQuery

class CourseExecutionBackendCreate(BaseModel):
    execution_backend_id: str
    course_id: str
    properties: Optional[dict] = None

class CourseExecutionBackendGet(BaseEntityGet):
    execution_backend_id: str
    course_id: str
    properties: Optional[dict] = None
    
    model_config = ConfigDict(from_attributes=True)
    
class CourseExecutionBackendList(BaseModel):
    execution_backend_id: str
    course_id: str
    
    model_config = ConfigDict(from_attributes=True)
    
class CourseExecutionBackendUpdate(BaseModel):
    properties: Optional[dict] = None

class CourseExecutionBackendQuery(ListQuery):
    execution_backend_id: Optional[str] = None
    course_id: Optional[str] = None
    properties: Optional[str] = None

def course_execution_backend_search(db: 'Session', query, params: Optional[CourseExecutionBackendQuery]):
    if params.execution_backend_id != None:
        query = query.filter(execution_backend_id == params.execution_backend_id)
    if params.course_id != None:
        query = query.filter(course_id == params.course_id)

    return query

class CourseExecutionBackendInterface(EntityInterface):
    create = CourseExecutionBackendCreate
    get = CourseExecutionBackendGet
    list = CourseExecutionBackendList
    update = CourseExecutionBackendUpdate
    query = CourseExecutionBackendQuery
    search = course_execution_backend_search
    endpoint = "course-execution-backends"
    model = None  # Set by backend
    cache_ttl = 600  # 10 minutes - backend configurations change infrequently