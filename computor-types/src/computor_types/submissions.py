"""Pydantic DTOs and query helpers for manual submission endpoints."""
from datetime import datetime
from typing import Any, List, Optional


    
from pydantic import BaseModel, ConfigDict, field_validator

from computor_types.base import BaseEntityList, EntityInterface, ListQuery
from computor_types.tasks import (
    TaskStatus,
    map_int_to_task_status,
    map_task_status_to_int,
)

class SubmissionCreate(BaseModel):
    """Payload describing a manual submission request."""

    submission_group_id: str
    version_identifier: Optional[str] = None
    submit: bool = False  # True = official submission, False = test/practice run

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

class SubmissionInterface(EntityInterface):
    """Entity interface mapping manual submissions to the Result model."""

    list = SubmissionListItem
    get = SubmissionListItem
    query = SubmissionQuery
