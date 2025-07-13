from pydantic import BaseModel, ConfigDict
from typing import Optional
from sqlalchemy.orm import Session
from ctutor_backend.interface.course_members import CourseMemberGet, CourseMemberList
from ctutor_backend.interface.base import BaseEntityGet, EntityInterface, ListQuery
from ctutor_backend.model.course import CourseMemberComment

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

def course_member_comment_search(db: Session, query, params: Optional[CourseMemberCommentQuery]):

    if params.id != None:
        query = query.filter(CourseMemberComment.id == params.id)
    if params.transmitter_id != None:
        query = query.filter(CourseMemberComment.transmitter_id == params.transmitter_id)
    if params.course_member_id != None:
        query = query.filter(CourseMemberComment.course_member_id == params.course_member_id)

    return query

class CourseMemberCommentInterface(EntityInterface):
    create = CourseMemberCommentCreate
    get = CourseMemberCommentGet
    list = CourseMemberCommentList
    update = CourseMemberCommentUpdate
    query = CourseMemberCommentQuery
    search = course_member_comment_search
    endpoint = "course-member-comments"
    model = CourseMemberComment