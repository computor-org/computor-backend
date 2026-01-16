"""Pydantic DTOs for artifact-related models."""
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, field_validator

from computor_types.base import BaseEntityList, EntityInterface, ListQuery
from computor_types.tasks import TaskStatus, map_int_to_task_status
from computor_types.grading import GradingStatus

# Forward reference imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
        from computor_types.results import ResultList

# ===============================
# SubmissionArtifact DTOs
# ===============================

class SubmissionArtifactCreate(BaseModel):
    """DTO for creating submission artifacts.

    This is used internally when processing submission uploads.
    The upload endpoint accepts SubmissionCreate which only has:
    - submission_group_id
    - version_identifier (optional)
    """
    submission_group_id: str
    version_identifier: Optional[str] = None

class SubmissionArtifactUpdate(BaseModel):
    """DTO for updating submission artifacts."""
    submit: Optional[bool] = None  # True = official submission, False = test/practice run
    properties: Optional[dict[str, Any]] = None

class SubmissionArtifactList(BaseEntityList):
    """List item representation for submission artifacts.

    Essential metadata is stored in proper database columns.
    Properties field is kept for legacy compatibility and future extensibility.
    """
    id: str
    submission_group_id: str
    uploaded_by_course_member_id: Optional[str] = None
    content_type: Optional[str] = None
    file_size: int
    bucket_name: str
    object_key: str
    uploaded_at: datetime
    version_identifier: Optional[str] = None
    submit: bool = False  # Whether this is an official submission
    properties: Optional[dict[str, Any]] = None  # Additional metadata
    latest_result: Optional['ResultList'] = None  # Latest successful result (status=0)

    model_config = ConfigDict(from_attributes=True)

class SubmissionArtifactGet(SubmissionArtifactList):
    """Detailed view of submission artifact with related data."""
    test_results_count: Optional[int] = None
    grades_count: Optional[int] = None
    reviews_count: Optional[int] = None
    latest_result: Optional['ResultList'] = None
    average_grade: Optional[float] = None

class SubmissionArtifactQuery(ListQuery):
    """Query parameters for listing submission artifacts."""
    id: Optional[str] = None
    submission_group_id: Optional[str] = None
    uploaded_by_course_member_id: Optional[str] = None
    content_type: Optional[str] = None
    version_identifier: Optional[str] = None  # Filter by version (e.g., "v1.0.0", "commit-abc123")
    submit: Optional[bool] = None  # Filter by official submissions (True) or test runs (False)
    latest: Optional[bool] = None  # If True, return only the most recent artifact (by uploaded_at)

class SubmissionArtifactInterface(EntityInterface):
    """Entity interface for submission artifacts."""
    list = SubmissionArtifactList
    get = SubmissionArtifactGet
    create = SubmissionArtifactCreate
    update = SubmissionArtifactUpdate
    query = SubmissionArtifactQuery

# ===============================
# SubmissionGrade DTOs
# ===============================

class SubmissionGradeCreate(BaseModel):
    """DTO for creating submission grades."""
    artifact_id: str
    graded_by_course_member_id: str
    grade: float
    status: GradingStatus = GradingStatus.NOT_REVIEWED
    comment: Optional[str] = None

class SubmissionGradeUpdate(BaseModel):
    """DTO for updating submission grades."""
    grade: Optional[float] = None
    status: Optional[GradingStatus] = None
    comment: Optional[str] = None

class SubmissionGradeListItem(BaseEntityList):
    """List item representation for submission grades."""
    id: str
    artifact_id: str
    graded_by_course_member_id: str
    grade: float
    status: GradingStatus
    comment: Optional[str] = None
    graded_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("status", mode="before")
    @classmethod
    def _coerce_status(cls, value):
        if isinstance(value, GradingStatus):
            return value
        return GradingStatus(value) if value is not None else GradingStatus.NOT_REVIEWED

class SubmissionGradeDetail(SubmissionGradeListItem):
    """Detailed view of submission grade."""
    pass  # No additional fields beyond the list item

class SubmissionGradeQuery(ListQuery):
    """Query parameters for listing submission grades."""
    id: Optional[str] = None
    artifact_id: Optional[str] = None
    graded_by_course_member_id: Optional[str] = None
    status: Optional[GradingStatus] = None

class SubmissionGradeInterface(EntityInterface):
    """Entity interface for submission grades."""
    list = SubmissionGradeListItem
    get = SubmissionGradeDetail
    create = SubmissionGradeCreate
    update = SubmissionGradeUpdate
    query = SubmissionGradeQuery

# ===============================
# SubmissionReview DTOs
# ===============================

class SubmissionReviewCreate(BaseModel):
    """DTO for creating submission reviews."""
    artifact_id: str
    reviewer_course_member_id: str
    body: str
    review_type: Optional[str] = None

class SubmissionReviewUpdate(BaseModel):
    """DTO for updating submission reviews."""
    body: Optional[str] = None
    review_type: Optional[str] = None

class SubmissionReviewListItem(BaseEntityList):
    """List item representation for submission reviews."""
    id: str
    artifact_id: str
    reviewer_course_member_id: str
    body: str
    review_type: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SubmissionReviewDetail(SubmissionReviewListItem):
    """Detailed view of submission review."""
    pass  # Same as list item for now

class SubmissionReviewQuery(ListQuery):
    """Query parameters for listing submission reviews."""
    id: Optional[str] = None
    artifact_id: Optional[str] = None
    reviewer_course_member_id: Optional[str] = None
    review_type: Optional[str] = None

class SubmissionReviewInterface(EntityInterface):
    """Entity interface for submission reviews."""
    list = SubmissionReviewListItem
    get = SubmissionReviewDetail
    create = SubmissionReviewCreate
    update = SubmissionReviewUpdate
    query = SubmissionReviewQuery

# ===============================
# ResultArtifact DTOs
# ===============================

class ResultArtifactCreate(BaseModel):
    """DTO for creating result artifacts."""
    result_id: str
    content_type: Optional[str] = None
    file_size: int
    bucket_name: str
    object_key: str
    properties: Optional[dict[str, Any]] = None

class ResultArtifactListItem(BaseEntityList):
    """List item representation for result artifacts."""
    id: str
    result_id: str
    content_type: Optional[str] = None
    file_size: int
    bucket_name: str
    object_key: str
    created_at: datetime
    properties: Optional[dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

class ResultArtifactQuery(ListQuery):
    """Query parameters for listing result artifacts."""
    id: Optional[str] = None
    result_id: Optional[str] = None
    content_type: Optional[str] = None

class ResultArtifactInterface(EntityInterface):
    """Entity interface for result artifacts."""
    list = ResultArtifactListItem
    get = ResultArtifactListItem
    create = ResultArtifactCreate
    query = ResultArtifactQuery


# ===============================
# Result Artifact Upload DTOs
# ===============================

class ArtifactInfo(BaseModel):
    """Information about a single uploaded artifact."""
    filename: str
    file_size: int
    content_type: Optional[str] = None


class ResultArtifactUploadResponse(BaseModel):
    """Response for artifact upload endpoint."""
    result_id: str
    artifacts_count: int
    artifacts: List[ArtifactInfo]


# Import the necessary types first
from .results import ResultList

# Rebuild all models that have forward references
SubmissionArtifactGet.model_rebuild()