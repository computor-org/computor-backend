import json
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from computor_types.base import BaseEntityGet, BaseEntityList, EntityInterface, ListQuery

from computor_types.tasks import TaskStatus, map_int_to_task_status

class ResultCreate(BaseModel):
    course_member_id: str
    course_content_id: str
    submission_group_id: str = None
    submission_artifact_id: Optional[str] = None
    execution_backend_id: Optional[str] = None
    test_system_id: Optional[str] = None
    result: float
    grade: Optional[float] = None
    result_json: Optional[dict | None] = None
    properties: Optional[dict | None] = None
    version_identifier: str
    reference_version_identifier: Optional[str] = None
    status: TaskStatus
    
    model_config = ConfigDict(from_attributes=True)

    @field_validator("status", mode="before")
    @classmethod
    def _coerce_status(cls, value):
        if isinstance(value, TaskStatus):
            return value
        return map_int_to_task_status(value)

class ResultGet(BaseEntityGet):
    id: str
    course_member_id: str
    course_content_id: str
    course_content_type_id: str
    submission_group_id: Optional[str] = None
    submission_artifact_id: Optional[str] = None
    execution_backend_id: Optional[str] = None
    test_system_id: Optional[str] = None
    result: float
    grade: Optional[float] = None
    result_json: Optional[dict | None] = None
    properties: Optional[dict | None] = None
    version_identifier: str
    reference_version_identifier: Optional[str] = None
    status: TaskStatus
    # New: relationship to gradings
    grading_ids: Optional[List[str]] = []  # IDs of gradings that reference this result
    
    model_config = ConfigDict(from_attributes=True)

    @field_validator("status", mode="before")
    @classmethod
    def _coerce_status(cls, value):
        if isinstance(value, TaskStatus):
            return value
        return map_int_to_task_status(value)

class ResultList(BaseEntityList):
    id: str
    course_member_id: str
    course_content_id: str
    course_content_type_id: str
    submission_group_id: Optional[str] = None
    submission_artifact_id: Optional[str] = None
    execution_backend_id: Optional[str] = None
    test_system_id: Optional[str] = None
    result: float
    grade: Optional[float] = None
    version_identifier: str
    reference_version_identifier: Optional[str] = None
    status: TaskStatus

    model_config = ConfigDict(from_attributes=True)

    @field_validator("status", mode="before")
    @classmethod
    def _coerce_status(cls, value):
        if isinstance(value, TaskStatus):
            return value
        return map_int_to_task_status(value)
    
class ResultUpdate(BaseModel):
    result: Optional[float | None] = None
    grade: Optional[float | None] = None
    result_json: Optional[dict | None] = None
    status: Optional[TaskStatus | None] = None
    test_system_id: Optional[str] = None
    properties: Optional[dict | None] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("status", mode="before")
    @classmethod
    def _coerce_status(cls, value):
        if value is None or isinstance(value, TaskStatus):
            return value
        return map_int_to_task_status(value)

class ResultQuery(ListQuery):
    id: Optional[str] = None
    submitter_id: Optional[str] = None
    course_member_id: Optional[str] = None
    course_content_id: Optional[str] = None
    course_content_type_id: Optional[str] = None
    submission_group_id: Optional[str] = None
    submission_artifact_id: Optional[str] = None
    execution_backend_id: Optional[str] = None
    test_system_id: Optional[str ] = None
    version_identifier: Optional[str] = None
    status: Optional[TaskStatus] = None
    latest: Optional[bool] = False
    result: Optional[float] = None
    grade: Optional[float] = None
    result_json: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

# Backend function - moved to backend in Phase 4
# def result_search(db: 'Session', query, params: Optional[ResultQuery]):
#     """Search function using SQLAlchemy models - belongs in backend."""
#     ...

# Backend function - moved to backend in Phase 4
# async def post_update_result(updated_entity: Result, old_entity, db: Session):
#     """Post-update hook to invalidate view caches when results change."""
#     ...

class ResultInterface(EntityInterface):
    create = ResultCreate
    get = ResultGet
    list = ResultList
    update = ResultUpdate
    query = ResultQuery
    search = None  # Moved to backend in Phase 4
    endpoint = "results"
    model = None  # Set by backend
    cache_ttl = 60  # 1 minute - results change frequently as students submit work
    # post_update = staticmethod(post_update_result)  # Moved to backend

# Extended Result DTOs
class ResultWithGrading(ResultGet):
    """Result with associated grading information."""
    latest_grading: Optional[dict] = None  # Latest grading for this result
    grading_count: int = 0  # Number of times this result has been graded
    
    model_config = ConfigDict(from_attributes=True)