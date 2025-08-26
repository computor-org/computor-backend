from datetime import datetime
from pydantic import BaseModel, field_validator, ConfigDict
from typing import Literal, Optional, List
from sqlalchemy import and_, func
from sqlalchemy.orm import Session
from ctutor_backend.interface.course_content_types import CourseContentTypeGet, CourseContentTypeList
from ctutor_backend.interface.deployments import GitLabConfigGet
from ctutor_backend.interface.base import BaseEntityGet, EntityInterface, ListQuery
from ctutor_backend.interface.results import ResultStatus
from ctutor_backend.model.course import CourseContent
from ctutor_backend.model.course import CourseMember
from ..custom_types import Ltree

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

class SubmissionGroupGradingStudent(BaseModel):
    """Student's view of grading"""
    id: str
    grading: float  # 0.0 to 1.0
    status: Optional[str] = None  # corrected, correction_necessary, etc.
    graded_by: Optional[str] = None  # Name of grader
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class SubmissionGroupStudentList(BaseModel):
    """Enhanced submission group data for course contents"""
    id: Optional[str] = None
    course_content_title: Optional[str] = None
    course_content_path: Optional[str] = None
    example_identifier: Optional[str] = None  # The example.identifier for directory structure
    max_group_size: Optional[int] = None
    current_group_size: int = 1
    members: List[SubmissionGroupMemberBasic] = []
    repository: Optional[SubmissionGroupRepository] = None
    latest_grading: Optional[SubmissionGroupGradingStudent] = None
    status: Optional[str] = None  # Backward compatibility
    grading: Optional[float] = None  # Backward compatibility
    count: int = 0  # Backward compatibility - submission count
    max_submissions: Optional[int] = None  # Backward compatibility
    
    model_config = ConfigDict(from_attributes=True)

class ResultStudentList(BaseModel):
    execution_backend_id: Optional[str] = None
    test_system_id: Optional[str] = None
    version_identifier: Optional[str] = None
    status: Optional[ResultStatus] = None
    result: Optional[float] = None
    result_json: Optional[dict] = None
    submit: Optional[bool] = None

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
    course_content_types: CourseContentTypeGet
    result_count: int
    max_test_runs: Optional[int] = None

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
    max_test_runs: Optional[int] = None

    directory: Optional[str] = None
    color: str

    result: Optional[ResultStudentList] = None

    submission_group:  Optional[SubmissionGroupStudentList] = None
    
    @field_validator('path', mode='before')
    @classmethod
    def cast_str_to_ltree(cls, value):
        return str(value)

    model_config = ConfigDict(from_attributes=True)
    
class CourseContentStudentUpdate(BaseModel):
    status: Optional[Literal["corrected", "correction_necessary", "improvement_possible"]] = None
    grading: Optional[float] = None

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
    

def course_content_student_search(db: Session, query, params: Optional[CourseContentStudentQuery]):
    if params.id != None:
        query = query.filter(CourseContent.id == params.id)
    if params.title != None:
        query = query.filter(CourseContent.title == params.title)
    if params.path != None:
        query = query.filter(CourseContent.path == Ltree(params.path))
    if params.course_id != None:
        query = query.filter(CourseContent.course_id == params.course_id)
    if params.course_content_type_id != None:
        query = query.filter(CourseContent.course_content_type_id == params.course_content_type_id)

    # TODO: only for gitlab courses. This has to be checked
    if params.directory != None:
         query = query.filter(CourseContent.properties["gitlab"].op("->>")("directory") == params.directory)
    if params.project != None:
         query = query.filter(CourseMember.properties["gitlab"].op("->>")("full_path") == params.project)
    if params.provider_url != None:
         query = query.filter(CourseMember.properties["gitlab"].op("->>")("url") == params.provider_url)

    if params.nlevel != None:
        query = query.filter(func.nlevel(CourseContent.path) == params.nlevel)
    if params.descendants != None:
        query = query.filter(and_(CourseContent.path.descendant_of(Ltree(params.descendants)), CourseContent.path != Ltree(params.descendants)))
    if params.ascendants != None:
        query = query.filter(and_(CourseContent.path.ancestor_of(Ltree(params.ascendants)), CourseContent.path != Ltree(params.ascendants)))
    
    query = query.order_by(CourseContent.position)

    return query

class CourseContentStudentInterface(EntityInterface):
    create = None
    get = CourseContentStudentGet
    list = CourseContentStudentList
    update = CourseContentStudentUpdate
    query = CourseContentStudentQuery
    search = course_content_student_search
    endpoint = "student-course-contents"
    cache_ttl = 180  # 3 minutes - course content changes frequently during active sessions