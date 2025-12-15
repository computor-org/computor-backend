from pydantic import BaseModel, ConfigDict
from typing import Optional


    
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
    course_member_id: str
    submission_group_id: str
    grading: Optional[float] = None
    status: Optional[str] = None
    properties: Optional[SubmissionGroupMemberProperties] = None

    model_config = ConfigDict(from_attributes=True)

class SubmissionGroupMemberList(BaseModel):
    id: str
    course_id: str
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


class SubmissionGroupMemberInterface(EntityInterface):
    create = SubmissionGroupMemberCreate
    get = SubmissionGroupMemberGet
    list = SubmissionGroupMemberList
    update = SubmissionGroupMemberUpdate
    query = SubmissionGroupMemberQuery
