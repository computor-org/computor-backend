from pydantic import BaseModel, ConfigDict
from typing import Optional


    
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


class CourseRoleInterface(EntityInterface):
    create = None
    get = CourseRoleGet
    list = CourseRoleList
    update = None
    query = CourseRoleQuery
