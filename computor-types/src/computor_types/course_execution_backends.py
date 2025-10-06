from pydantic import BaseModel, ConfigDict
from typing import Optional


    
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


class CourseExecutionBackendInterface(EntityInterface):
    create = CourseExecutionBackendCreate
    get = CourseExecutionBackendGet
    list = CourseExecutionBackendList
    update = CourseExecutionBackendUpdate
    query = CourseExecutionBackendQuery
