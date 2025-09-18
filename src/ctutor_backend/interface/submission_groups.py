from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from sqlalchemy.orm import Session
from ctutor_backend.interface.deployments import GitLabConfig
from ctutor_backend.interface.base import EntityInterface, ListQuery, BaseEntityGet
from ctutor_backend.model.course import CourseSubmissionGroup

class SubmissionGroupProperties(BaseModel):
    gitlab: Optional[GitLabConfig] = None
    
    model_config = ConfigDict(
        extra='allow',
    )
    
class SubmissionGroupCreate(BaseModel):
    properties: Optional[SubmissionGroupProperties] = None
    max_group_size: int = 1
    max_submissions: Optional[int] = None
    course_content_id: str
    status: Optional[str] = None

class SubmissionGroupGet(BaseEntityGet, SubmissionGroupCreate):
    id: str
    course_id: str
    status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
class SubmissionGroupList(BaseModel):
    id: str
    properties: Optional[SubmissionGroupProperties] = None
    max_group_size: int
    max_submissions: Optional[int] = None
    course_id: str
    course_content_id: str
    status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
    
class SubmissionGroupUpdate(BaseModel):
    properties: Optional[SubmissionGroupProperties] = None
    max_group_size: Optional[int] = None
    max_submissions: Optional[int] = None
    status: Optional[str] = None

class SubmissionGroupQuery(ListQuery):
    id: Optional[str] = None
    max_group_size: Optional[int] = None
    max_submissions: Optional[int] = None
    course_id: Optional[str] = None
    course_content_id: Optional[str] = None
    properties: Optional[SubmissionGroupProperties] = None
    status: Optional[str] = None

def submission_group_search(db: Session, query, params: Optional[SubmissionGroupQuery]):
    if params.id != None:
        query = query.filter(CourseSubmissionGroup.id == params.id)
    if params.max_group_size != None:
        query = query.filter(CourseSubmissionGroup.max_group_size == params.max_group_size)
    if params.max_submissions != None:
        query = query.filter(CourseSubmissionGroup.max_submissions == params.max_submissions)
    if params.course_id != None:
        query = query.filter(CourseSubmissionGroup.course_id == params.course_id)
    if params.course_content_id != None:
        query = query.filter(CourseSubmissionGroup.course_content_id == params.course_content_id)
    # Note: status has been moved to CourseSubmissionGroupGrading
    # This filter needs to be rewritten to join with the grading table
    # if params.status != None:
    #     query = query.filter(CourseSubmissionGroup.status == params.status)
        
    return query

class SubmissionGroupInterface(EntityInterface):
    create = SubmissionGroupCreate
    get = SubmissionGroupGet
    list = SubmissionGroupList
    update = SubmissionGroupUpdate
    query = SubmissionGroupQuery
    search = submission_group_search
    endpoint = "submission-groups"
    model = CourseSubmissionGroup
    cache_ttl = 120  # 2 minutes - submission groups change moderately frequently


# # Student-specific DTOs
# class SubmissionGroupRepository(BaseModel):
#     """Repository information for a submission group"""
#     provider: str = "gitlab"  # gitlab, github, etc.
#     url: str                  # Base URL
#     full_path: str            # Organization/project path
#     clone_url: Optional[str] = None  # Full clone URL
#     web_url: Optional[str] = None    # Web interface URL
    
#     model_config = ConfigDict(from_attributes=True)


# class SubmissionGroupMemberBasic(BaseModel):
#     """Basic member information"""
#     id: str
#     user_id: str
#     course_member_id: str
#     username: Optional[str] = None
#     full_name: Optional[str] = None
    
#     model_config = ConfigDict(from_attributes=True)


# class SubmissionGroupGradingStudent(BaseModel):
#     """Student's view of grading"""
#     id: str
#     grading: float  # 0.0 to 1.0
#     status: Optional[str] = None  # corrected, correction_necessary, etc.
#     graded_by: Optional[str] = None  # Name of grader
#     created_at: datetime
    
#     model_config = ConfigDict(from_attributes=True)


# class SubmissionGroupStudent(BaseModel):
#     """Student's view of a submission group"""
#     id: str
#     course_id: str
#     course_content_id: str
#     course_content_title: Optional[str] = None
#     course_content_path: Optional[str] = None
#     example_identifier: Optional[str] = None  # The example.identifier for directory structure
#     max_group_size: int
#     current_group_size: int = 1
#     members: List[SubmissionGroupMemberBasic] = []
#     repository: Optional[SubmissionGroupRepository] = None
#     latest_grading: Optional[SubmissionGroupGradingStudent] = None
#     created_at: datetime
#     updated_at: datetime
    
#     model_config = ConfigDict(from_attributes=True)


class SubmissionGroupStudentQuery(BaseModel):
    """Query parameters for student submission groups"""
    course_id: Optional[str] = None
    course_content_id: Optional[str] = None
    has_repository: Optional[bool] = None
    is_graded: Optional[bool] = None