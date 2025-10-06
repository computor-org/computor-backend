from pydantic import BaseModel, ConfigDict
from typing import Optional


    
from computor_types.course_members import CourseMemberGet, CourseMemberList
from computor_types.base import BaseEntityGet, EntityInterface, ListQuery

class CourseMemberCommentCreate(BaseModel):
    id: Optional[str] = None
    transmitter_id: str = None
    course_member_id: str
    message: str

class CourseMemberCommentGet(BaseEntityGet):
    id: str
    transmitter_id: str = None
    transmitter: CourseMemberGet
    course_member_id: str
    message: str

    model_config = ConfigDict(from_attributes=True)

class CourseMemberCommentList(BaseEntityGet):
    id: str
    transmitter_id: str = None
    transmitter: CourseMemberList
    course_member_id: str
    message: str

    model_config = ConfigDict(from_attributes=True)

class CourseMemberCommentUpdate(BaseModel):
    message: Optional[str] = None
    
class CourseMemberCommentQuery(ListQuery):
    id: Optional[str] = None
    transmitter_id: Optional[str] = None
    course_member_id: Optional[str] = None


class CourseMemberCommentInterface(EntityInterface):
    create = CourseMemberCommentCreate
    get = CourseMemberCommentGet
    list = CourseMemberCommentList
    update = CourseMemberCommentUpdate
    query = CourseMemberCommentQuery
