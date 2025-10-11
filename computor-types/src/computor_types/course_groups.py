from pydantic import BaseModel, ConfigDict
from typing import Optional


    
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

class CourseGroupInterface(EntityInterface):
    create = CourseGroupCreate
    get = CourseGroupGet
    list = CourseGroupList
    update = CourseGroupUpdate
    query = CourseGroupQuery
