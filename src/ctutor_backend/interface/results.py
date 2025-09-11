import json
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func
from ctutor_backend.interface.base import BaseEntityGet, EntityInterface, ListQuery
from ctutor_backend.model import CourseContentType, CourseSubmissionGroupMember
from ctutor_backend.model.course import CourseContent
from ctutor_backend.model.result import Result
from ctutor_backend.tasks.base import TaskStatus

def map_task_status_to_int(status: TaskStatus) -> int:
    """Map TaskStatus enum to legacy integer for database storage."""
    mapping = {
        TaskStatus.FINISHED: 0,    # FINISHED -> COMPLETED (0)
        TaskStatus.FAILED: 1,      # FAILED -> FAILED (1)
        TaskStatus.CANCELLED: 2,   # CANCELLED -> CANCELLED (2)
        TaskStatus.QUEUED: 4,      # QUEUED -> PENDING (4)
        TaskStatus.STARTED: 5,     # STARTED -> RUNNING (5)
        TaskStatus.DEFERRED: 7     # DEFERRED -> PAUSED (7)
    }
    return mapping.get(status, 1)  # Default to FAILED (1)

class ResultCreate(BaseModel):
    submit: bool
    course_member_id: str
    course_content_id: str
    course_submission_group_id: str = None
    execution_backend_id: str
    test_system_id: str
    result: float
    result_json: Optional[dict | None] = None
    properties: Optional[dict | None] = None
    version_identifier: str
    status: TaskStatus
    
    model_config = ConfigDict(from_attributes=True)

class ResultGet(BaseEntityGet):
    id: str
    submit: bool
    course_member_id: str
    course_content_id: str
    course_content_type_id: str
    course_submission_group_id: Optional[str] = None
    execution_backend_id: str
    test_system_id: str
    result: float
    result_json: Optional[dict | None] = None
    properties: Optional[dict | None] = None
    version_identifier: str
    status: TaskStatus
    # New: relationship to gradings
    grading_ids: Optional[List[str]] = []  # IDs of gradings that reference this result
    
    model_config = ConfigDict(from_attributes=True)

class ResultList(BaseModel):
    id: str
    submit: bool
    course_member_id: str
    course_content_id: str
    course_content_type_id: str
    course_submission_group_id: Optional[str] = None
    execution_backend_id: str
    test_system_id: str
    result: float
    version_identifier: str
    status: TaskStatus

    model_config = ConfigDict(from_attributes=True)
    
class ResultUpdate(BaseModel):
    submit: Optional[bool | None] = None
    result: Optional[float | None] = None
    result_json: Optional[dict | None] = None
    status: Optional[TaskStatus | None] = None
    test_system_id: Optional[str | None] = None
    properties: Optional[dict | None] = None

    model_config = ConfigDict(from_attributes=True)

class ResultQuery(ListQuery):
    id: Optional[str] = None
    submit: Optional[bool] = None
    submitter_id: Optional[str] = None
    course_member_id: Optional[str] = None
    course_content_id: Optional[str] = None
    course_content_type_id: Optional[str] = None
    course_submission_group_id: Optional[str] = None
    execution_backend_id: Optional[str] = None
    test_system_id: Optional[str ] = None
    version_identifier: Optional[str] = None
    status: Optional[TaskStatus] = None
    latest: Optional[bool] = False
    result: Optional[float] = None
    result_json: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

def result_search(db: Session, query, params: Optional[ResultQuery]):

    latest_group_by_conditions = []
    latest_join_by_conditions = []

    query = query.join(CourseContentType, CourseContentType.id == Result.course_content_type_id)

    if params.id != None:
        query = query.filter(Result.id == params.id)
        latest_group_by_conditions.append(Result.id)
        latest_join_by_conditions.append(lambda subquery: Result.id == subquery.c.id)
    if params.submit != None:
        query = query.filter(Result.submit == params.submit)
    if params.submitter_id != None:
        query = query.filter(Result.course_member_id == params.submitter_id)
        latest_group_by_conditions.append(Result.course_member_id)
        latest_join_by_conditions.append(lambda subquery: Result.course_member_id == subquery.c.course_member_id)

    if params.course_member_id != None:
        query = query.join(CourseSubmissionGroupMember,CourseSubmissionGroupMember.course_submission_group_id == Result.course_submission_group_id) \
            .filter(CourseSubmissionGroupMember.course_member_id == params.course_member_id)

        latest_group_by_conditions.append(Result.course_submission_group_id)
        latest_join_by_conditions.append(lambda subquery: Result.course_submission_group_id == subquery.c.course_submission_group_id)

    if params.course_content_id != None:
        query = query.filter(Result.course_content_id == params.course_content_id)
    if params.course_content_type_id != None:
        query = query.filter(Result.course_content_type_id == params.course_content_type_id)
    if params.course_submission_group_id != None:
        query = query.filter(Result.course_submission_group_id == params.course_submission_group_id)
        latest_group_by_conditions.append(Result.course_submission_group_id)
        latest_join_by_conditions.append(lambda subquery: Result.course_submission_group_id == subquery.c.course_submission_group_id)
    if params.execution_backend_id != None:
        query = query.filter(Result.execution_backend_id == params.execution_backend_id)
        latest_group_by_conditions.append(Result.execution_backend_id)
        latest_join_by_conditions.append(lambda subquery: Result.execution_backend_id == subquery.c.execution_backend_id)
    if params.test_system_id != None:
        query = query.filter(Result.test_system_id == params.test_system_id)
        latest_group_by_conditions.append(Result.test_system_id)
        latest_join_by_conditions.append(lambda subquery: Result.test_system_id == subquery.c.test_system_id)
    if params.version_identifier != None:
        query = query.filter(Result.version_identifier == params.version_identifier)
        latest_group_by_conditions.append(Result.version_identifier)
        latest_join_by_conditions.append(lambda subquery: Result.version_identifier == subquery.c.version_identifier)
    if params.status != None:
        query = query.filter(Result.status == params.status)
        latest_group_by_conditions.append(Result.status)
        latest_join_by_conditions.append(lambda subquery: Result.status == subquery.c.status)
    if params.result != None:
        query = query.filter(Result.result == params.result)
        latest_group_by_conditions.append(Result.result)
        latest_join_by_conditions.append(lambda subquery: Result.result == subquery.c.result)

    if params.result_json != None:
        result_json = json.loads(params.result_json)
        query = query.filter(Result.result_json == result_json)

    if params.latest == True:

        subquery = select(*latest_group_by_conditions, Result.course_content_id, func.max(Result.created_at).label('latest_created_at')) \
            .group_by(*latest_group_by_conditions, Result.course_content_id) \
            .subquery()

        conditions = []
        conditions.append(Result.created_at == subquery.c.latest_created_at)
        conditions.append(Result.course_content_id == subquery.c.course_content_id)

        for latest_join_by_condition in latest_join_by_conditions:
            conditions.append(latest_join_by_condition(subquery))
        
        query = query.join(subquery, and_(*conditions)) \
            .join(CourseContent,CourseContent.id == Result.course_content_id) \
            .order_by(CourseContent.path)
    else:
        query = query.order_by(Result.created_at.desc())

    return query

class ResultInterface(EntityInterface):
    create = ResultCreate
    get = ResultGet
    list = ResultList
    update = ResultUpdate
    query = ResultQuery
    search = result_search
    endpoint = "results"
    model = Result
    cache_ttl = 60  # 1 minute - results change frequently as students submit work


# Extended Result DTOs
class ResultWithGrading(ResultGet):
    """Result with associated grading information."""
    latest_grading: Optional[dict] = None  # Latest grading for this result
    grading_count: int = 0  # Number of times this result has been graded
    
    model_config = ConfigDict(from_attributes=True)


class ResultDetailed(BaseModel):
    """Detailed result information including submission group and grading."""
    id: str
    submit: bool
    course_member_id: str
    course_member_name: Optional[str] = None  # Name of the submitter
    course_content_id: str
    course_content_title: Optional[str] = None
    course_content_path: Optional[str] = None
    course_content_type_id: str
    course_submission_group_id: Optional[str] = None
    submission_group_members: Optional[List[dict]] = []  # Group member info
    execution_backend_id: str
    test_system_id: str
    result: float
    result_json: Optional[dict | None] = None
    properties: Optional[dict | None] = None
    version_identifier: str
    status: TaskStatus
    
    # Grading information
    gradings: List[dict] = []  # All gradings for this result
    latest_grade: Optional[float] = None
    latest_grading_status: Optional[int] = None  # GradingStatus value
    latest_grading_feedback: Optional[str] = None
    
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)