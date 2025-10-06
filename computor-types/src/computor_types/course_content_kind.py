from pydantic import BaseModel, ConfigDict
from typing import Optional


    
from computor_types.base import BaseEntityGet, EntityInterface, ListQuery

    
class CourseContentKindCreate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    has_ascendants: bool
    has_descendants: bool
    submittable: bool

class CourseContentKindGet(BaseEntityGet,CourseContentKindCreate):
    id: str

    model_config = ConfigDict(from_attributes=True)

class CourseContentKindList(BaseModel):
    id: str
    title: Optional[str] = None
    has_ascendants: bool
    has_descendants: bool
    submittable: bool

    model_config = ConfigDict(from_attributes=True)

class CourseContentKindUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None

class CourseContentKindQuery(ListQuery):
    id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    has_ascendants: Optional[bool] = None
    has_descendants: Optional[bool] = None
    submittable: Optional[bool] = None


class CourseContentKindInterface(EntityInterface):
    create = CourseContentKindCreate
    get = CourseContentKindGet
    list = CourseContentKindList
    update = CourseContentKindUpdate
    query = CourseContentKindQuery
