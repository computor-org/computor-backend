from datetime import datetime
from pydantic import BaseModel, field_validator, ConfigDict, Field
from typing import Literal, Optional, List, TYPE_CHECKING

from computor_types.course_content_types import CourseContentTypeGet, CourseContentTypeList
from computor_types.deployments import GitLabConfigGet
from computor_types.base import BaseEntityGet, EntityInterface, ListQuery
from computor_types.tasks import TaskStatus
from computor_types.grading import SubmissionGroupGradingList, GradedByCourseMember
from computor_types.deployment import CourseContentDeploymentList
from computor_types.results import ResultArtifactInfo

from computor_types.custom_types import Ltree

class SubmissionGroupRepository(BaseModel):
    """Repository information for a submission group"""
    provider: str = "gitlab"  # gitlab, github, etc.
    url: str                  # Base URL
    full_path: str            # Organization/project path
    clone_url: Optional[str] = None  # Full clone URL
    web_url: Optional[str] = None    # Web interface URL
    
    model_config = ConfigDict(from_attributes=True)

class SubmissionGroupMemberBasic(BaseModel):
    """Basic member information"""
    id: str
    user_id: str
    course_member_id: str
    username: Optional[str] = None
    full_name: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

# class SubmissionGroupGradingStudent(BaseModel):
#     """Student's view of grading"""
#     id: str
#     grading: float  # 0.0 to 1.0
#     status: Optional[str] = None  # corrected, correction_necessary, etc.
#     graded_by: Optional[str] = None  # Name of grader
#     created_at: datetime
    
#     model_config = ConfigDict(from_attributes=True)

class SubmissionGroupStudentList(BaseModel):
    """Submission group data for course contents (list view)."""
    id: Optional[str] = None
    course_content_title: Optional[str] = None
    course_content_path: Optional[str] = None
    example_identifier: Optional[str] = None  # The example.identifier for directory structure
    max_group_size: Optional[int] = None
    current_group_size: int = 1
    members: List[SubmissionGroupMemberBasic] = []
    repository: Optional[SubmissionGroupRepository] = None
    status: Optional[str] = None  # Backward compatibility
    grading: Optional[float] = None  # Backward compatibility
    graded_by_course_member: Optional[GradedByCourseMember] = None  # Who graded this
    count: int = 0  # Backward compatibility - submission count
    max_submissions: Optional[int] = None  # Backward compatibility
    unread_message_count: int = 0

    model_config = ConfigDict(from_attributes=True)

class SubmissionGroupStudentGet(SubmissionGroupStudentList):
    """Detailed submission group view including grading history."""
    gradings: List[SubmissionGroupGradingList] = Field(default_factory=list)

class ResultStudentList(BaseModel):
    id: str
    testing_service_id: Optional[str] = None
    test_system_id: Optional[str] = None
    version_identifier: Optional[str] = None
    status: Optional[TaskStatus] = None
    result: Optional[float] = None
    submit: Optional[bool] = None

class ResultStudentGet(ResultStudentList):
    result_json: Optional[dict] = None
    result_artifacts: List[ResultArtifactInfo] = []

class CourseContentStudentProperties(BaseModel):
    gitlab: Optional[GitLabConfigGet] = None
    
    model_config = ConfigDict(
        extra='allow',
    )

class CourseContentStudentGet(BaseEntityGet):
    id: str
    archived_at: Optional[datetime] = None
    title: Optional[str] = None
    description: Optional[str] = None
    path: str
    course_id: str
    course_content_type_id: str
    course_content_kind_id: str
    position: float
    max_group_size: Optional[int] = None
    submitted: Optional[bool] = None
    course_content_type: CourseContentTypeGet
    result_count: int
    submission_count: int
    max_test_runs: Optional[int] = None
    testing_service_id: Optional[str] = None
    unread_message_count: int = 0
    result: Optional[ResultStudentGet] = None
    directory: Optional[str] = None
    color: str
    submission_group: Optional[SubmissionGroupStudentGet] = None
    deployment: Optional[CourseContentDeploymentList] = None
    has_deployment: Optional[bool] = None

    # Aggregated status for unit-like course contents (non-submittable)
    # For submittable contents, this mirrors submission_group.status
    # For units, this is aggregated from descendant course contents
    status: Optional[str] = None

    # Whether the latest submission is unreviewed
    # For assignments: 0 (reviewed) or 1 (unreviewed/no grades)
    # For units: count of descendant assignments with unreviewed latest submissions
    unreviewed_count: int = 0

    # Latest grade status for the latest submission artifact
    # "not_reviewed", "corrected", "correction_necessary", "improvement_possible"
    # None if no submissions or no grades on latest submission
    latest_grade_status: Optional[str] = None

    @field_validator('path', mode='before')
    @classmethod
    def cast_str_to_ltree(cls, value):
        return str(value)

    model_config = ConfigDict(from_attributes=True)

class CourseContentStudentList(BaseModel):
    id: str
    title: Optional[str] = None
    path: str
    course_id: str
    course_content_type_id: str
    course_content_kind_id: str
    position: float
    max_group_size: Optional[int] = None
    submitted: Optional[bool] = None
    course_content_type: CourseContentTypeList
    result_count: int
    submission_count: int
    max_test_runs: Optional[int] = None
    testing_service_id: Optional[str] = None

    directory: Optional[str] = None
    color: str

    result: Optional[ResultStudentList] = None

    submission_group:  Optional[SubmissionGroupStudentList] = None
    unread_message_count: int = 0
    deployment: Optional[CourseContentDeploymentList] = None
    has_deployment: Optional[bool] = None

    # Aggregated status for unit-like course contents (non-submittable)
    # For submittable contents, this mirrors submission_group.status
    # For units, this is aggregated from descendant course contents
    status: Optional[str] = None

    # Whether the latest submission is unreviewed
    # For assignments: 0 (reviewed) or 1 (unreviewed/no grades)
    # For units: count of descendant assignments with unreviewed latest submissions
    unreviewed_count: int = 0

    # Latest grade status for the latest submission artifact
    # "not_reviewed", "corrected", "correction_necessary", "improvement_possible"
    # None if no submissions or no grades on latest submission
    latest_grade_status: Optional[str] = None

    @field_validator('path', mode='before')
    @classmethod
    def cast_str_to_ltree(cls, value):
        return str(value)

    model_config = ConfigDict(from_attributes=True)

class CourseContentStudentUpdate(BaseModel):
    status: Optional[Literal["corrected", "correction_necessary", "improvement_possible", "not_reviewed"]] = None
    grading: Optional[float] = None
    feedback: Optional[str] = None  # Optional feedback/comments from the grader

class CourseContentStudentQuery(ListQuery):
    id: Optional[str] = None
    title: Optional[str] = None
    path: Optional[str] = None
    course_id: Optional[str] = None
    course_content_type_id: Optional[str] = None
    
    directory: Optional[str] = None
    project: Optional[str] = None
    provider_url: Optional[str] = None

    nlevel: Optional[int] = None
    descendants: Optional[str] = None
    ascendants: Optional[str] = None
    
class CourseContentStudentInterface(EntityInterface):
    create = None
    get = CourseContentStudentGet
    list = CourseContentStudentList
    update = CourseContentStudentUpdate
    query = CourseContentStudentQuery
