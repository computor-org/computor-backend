from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional, List


    
from computor_types.deployments import GitLabConfig
from computor_types.base import EntityInterface, ListQuery, BaseEntityGet
from computor_types.grading import GradingStatus

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
    status: Optional[str] = None  # Deprecated - use latest grading status
    last_submitted_result_id: Optional[str] = None  # ID of the last submitted result

    model_config = ConfigDict(from_attributes=True)
class SubmissionGroupList(BaseModel):
    id: str
    properties: Optional[SubmissionGroupProperties] = None
    max_group_size: int
    max_submissions: Optional[int] = None
    course_id: str
    course_content_id: str
    status: Optional[str] = None  # Deprecated - use latest grading status
    last_submitted_result_id: Optional[str] = None  # ID of the last submitted result

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


class SubmissionGroupInterface(EntityInterface):
    create = SubmissionGroupCreate
    get = SubmissionGroupGet
    list = SubmissionGroupList
    update = SubmissionGroupUpdate
    query = SubmissionGroupQuery

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

# Extended DTOs that include grading information
class SubmissionGroupWithGrading(SubmissionGroupGet):
    """Submission group with latest grading information."""
    latest_grading: Optional[dict] = None  # Latest grading info
    grading_count: int = 0  # Total number of gradings
    last_submitted_at: Optional[datetime] = None  # When the last result was submitted
    
    model_config = ConfigDict(from_attributes=True)

class SubmissionGroupDetailed(BaseModel):
    """Detailed submission group information including members and gradings."""
    id: str
    course_id: str
    course_content_id: str
    properties: Optional[SubmissionGroupProperties] = None
    max_group_size: int
    max_submissions: Optional[int] = None
    max_test_runs: Optional[int] = None
    
    # Related data
    members: List[dict] = []  # List of member info
    gradings: List[dict] = []  # List of all gradings
    last_submitted_result: Optional[dict] = None  # Last submitted result info
    
    # Computed fields
    current_group_size: int = 0
    submission_count: int = 0
    test_run_count: int = 0
    latest_grade: Optional[float] = None
    latest_grading_status: Optional[GradingStatus] = None
    
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)