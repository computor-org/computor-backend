from pydantic import BaseModel, ConfigDict
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from computor_types.deployments import GitLabConfig
from computor_types.base import EntityInterface, ListQuery, BaseEntityGet

class SubmissionGroupMemberProperties(BaseModel):
    gitlab: Optional[GitLabConfig] = None
    
    model_config = ConfigDict(
        extra='allow',
    )

class SubmissionGroupMemberCreate(BaseModel):
    course_member_id: str
    submission_group_id: str
    grading: Optional[float] = None
    properties: Optional[SubmissionGroupMemberProperties] = None

class SubmissionGroupMemberGet(BaseEntityGet):
    id: str
    course_id: str
    course_content_id: str
    course_member_id: str
    submission_group_id: str
    grading: Optional[float] = None
    status: Optional[str] = None
    properties: Optional[SubmissionGroupMemberProperties] = None

    model_config = ConfigDict(from_attributes=True)

class SubmissionGroupMemberList(BaseModel):
    id: str
    course_id: str
    course_content_id: str
    course_member_id: str
    submission_group_id: str
    grading: Optional[float] = None
    status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class SubmissionGroupMemberUpdate(BaseModel):
    course_id: Optional[str] = None
    grading: Optional[float] = None
    status: Optional[str] = None
    properties: Optional[SubmissionGroupMemberProperties] = None

class SubmissionGroupMemberQuery(ListQuery):
    id: Optional[str] = None
    course_id: Optional[str] = None
    course_content_id: Optional[str] = None
    course_member_id: Optional[str] = None
    submission_group_id: Optional[str] = None
    grading: Optional[float] = None
    status: Optional[str] = None
    properties: Optional[SubmissionGroupMemberProperties] = None

def submission_group_member_search(db: 'Session', query, params: Optional[SubmissionGroupMemberQuery]):
    if params.id != None:
        query = query.filter(id == params.id)
    if params.course_id != None:
        query = query.filter(course_id == params.course_id)
    if params.course_content_id != None:
        query = query.filter(course_content_id == params.course_content_id)
    if params.course_member_id != None:
        query = query.filter(course_member_id == params.course_member_id)
    if params.submission_group_id != None:
        query = query.filter(submission_group_id == params.submission_group_id)
    # Note: grading and status have been moved to SubmissionGroupGrading
    # These filters need to be rewritten to join with the grading table
    # if params.grading != None:
    #     query = query.filter(grading == params.grading)
    # if params.status != None:
    #     query = query.filter(status == params.status)
    
    return query

class SubmissionGroupMemberInterface(EntityInterface):
    create = SubmissionGroupMemberCreate
    get = SubmissionGroupMemberGet
    list = SubmissionGroupMemberList
    update = SubmissionGroupMemberUpdate
    query = SubmissionGroupMemberQuery
    search = submission_group_member_search
    endpoint = "submission-group-members"
    model = None  # Set by backend
    cache_ttl = 120  # 2 minutes - submission data changes moderately frequently