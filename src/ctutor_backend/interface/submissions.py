"""Pydantic DTOs and query helpers for manual submission endpoints."""
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.orm import Session

from ctutor_backend.interface.base import BaseEntityList, EntityInterface, ListQuery
from ctutor_backend.interface.tasks import (
    TaskStatus,
    map_int_to_task_status,
    map_task_status_to_int,
)
from ctutor_backend.model.result import Result


class SubmissionCreate(BaseModel):
    """Payload describing a manual submission request."""

    submission_group_id: str
    version_identifier: Optional[str] = None


class SubmissionUploadedFile(BaseModel):
    """Metadata about a file extracted from a submission archive."""

    object_key: str
    size: int
    content_type: str
    relative_path: str


class SubmissionUploadResponseModel(BaseModel):
    """Response returned after processing a manual submission."""

    artifacts: List[str]  # List of created SubmissionArtifact IDs
    submission_group_id: str
    uploaded_by_course_member_id: str
    total_size: int
    files_count: int
    uploaded_at: datetime
    version_identifier: str


class SubmissionListItem(BaseEntityList):
    """List item representation for manual submissions stored as results."""

    id: str
    submit: bool
    course_member_id: str
    course_content_id: str
    submission_group_id: Optional[str] = None
    execution_backend_id: Optional[str] = None
    test_system_id: Optional[str] = None
    version_identifier: str
    reference_version_identifier: Optional[str] = None
    status: TaskStatus
    result: float
    result_json: Optional[dict[str, Any] | None] = None
    properties: Optional[dict[str, Any] | None] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("status", mode="before")
    @classmethod
    def _coerce_status(cls, value):
        if isinstance(value, TaskStatus):
            return value
        return map_int_to_task_status(value)


class SubmissionQuery(ListQuery):
    """Query parameters for listing manual submissions."""

    id: Optional[str] = None
    submit: Optional[bool] = None
    course_member_id: Optional[str] = None
    submission_group_id: Optional[str] = None
    course_content_id: Optional[str] = None
    execution_backend_id: Optional[str] = None
    test_system_id: Optional[str] = None
    version_identifier: Optional[str] = None
    reference_version_identifier: Optional[str] = None
    status: Optional[TaskStatus] = None

    model_config = ConfigDict(from_attributes=True)


def submission_search(db: Session, query, params: SubmissionQuery):
    """Apply filters for manual submission listings based on query params."""

    if params.id is not None:
        query = query.filter(Result.id == params.id)
    if params.submit is not None:
        query = query.filter(Result.submit == params.submit)
    if params.course_member_id is not None:
        query = query.filter(Result.course_member_id == params.course_member_id)
    if params.submission_group_id is not None:
        query = query.filter(Result.submission_group_id == params.submission_group_id)
    if params.course_content_id is not None:
        query = query.filter(Result.course_content_id == params.course_content_id)
    if params.execution_backend_id is not None:
        query = query.filter(Result.execution_backend_id == params.execution_backend_id)
    if params.test_system_id is not None:
        query = query.filter(Result.test_system_id == params.test_system_id)
    if params.version_identifier is not None:
        query = query.filter(Result.version_identifier == params.version_identifier)
    if params.reference_version_identifier is not None:
        query = query.filter(Result.reference_version_identifier == params.reference_version_identifier)
    if params.status is not None:
        query = query.filter(Result.status == map_task_status_to_int(params.status))

    return query.order_by(Result.created_at.desc())


class SubmissionInterface(EntityInterface):
    """Entity interface mapping manual submissions to the Result model."""

    model = Result
    list = SubmissionListItem
    get = SubmissionListItem
    query = SubmissionQuery
    search = submission_search
