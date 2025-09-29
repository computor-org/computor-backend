"""Pydantic DTOs for artifact-related models."""
from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.orm import Session

from ctutor_backend.interface.base import BaseEntityList, EntityInterface, ListQuery
from ctutor_backend.interface.tasks import TaskStatus, map_int_to_task_status
from ctutor_backend.interface.grading import GradingStatus
from ctutor_backend.model.artifact import SubmissionArtifact, ResultArtifact, SubmissionGrade, SubmissionReview

# Forward reference imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ctutor_backend.interface.results import ResultList


# ===============================
# SubmissionArtifact DTOs
# ===============================

class SubmissionArtifactCreate(BaseModel):
    """DTO for creating submission artifacts."""
    submission_group_id: UUID
    original_filename: Optional[str] = None
    content_type: Optional[str] = None
    file_size: int
    bucket_name: str
    object_key: str
    properties: Optional[dict[str, Any]] = None


class SubmissionArtifactUpdate(BaseModel):
    """DTO for updating submission artifacts."""
    properties: Optional[dict[str, Any]] = None


class SubmissionArtifactListItem(BaseEntityList):
    """List item representation for submission artifacts."""
    id: UUID
    submission_group_id: UUID
    uploaded_by_course_member_id: Optional[UUID] = None
    original_filename: Optional[str] = None
    content_type: Optional[str] = None
    file_size: int
    bucket_name: str
    object_key: str
    uploaded_at: datetime
    properties: Optional[dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class SubmissionArtifactDetail(SubmissionArtifactListItem):
    """Detailed view of submission artifact with related data."""
    test_results_count: Optional[int] = None
    grades_count: Optional[int] = None
    reviews_count: Optional[int] = None
    latest_result: Optional['ResultList'] = None
    average_grade: Optional[float] = None


class SubmissionArtifactQuery(ListQuery):
    """Query parameters for listing submission artifacts."""
    id: Optional[UUID] = None
    submission_group_id: Optional[UUID] = None
    uploaded_by_course_member_id: Optional[UUID] = None
    content_type: Optional[str] = None


def submission_artifact_search(db: Session, query, params: SubmissionArtifactQuery):
    """Apply filters for submission artifact listings."""
    if params.id is not None:
        query = query.filter(SubmissionArtifact.id == params.id)
    if params.submission_group_id is not None:
        query = query.filter(SubmissionArtifact.submission_group_id == params.submission_group_id)
    if params.uploaded_by_course_member_id is not None:
        query = query.filter(SubmissionArtifact.uploaded_by_course_member_id == params.uploaded_by_course_member_id)
    if params.content_type is not None:
        query = query.filter(SubmissionArtifact.content_type == params.content_type)

    return query.order_by(SubmissionArtifact.uploaded_at.desc())


class SubmissionArtifactInterface(EntityInterface):
    """Entity interface for submission artifacts."""
    model = SubmissionArtifact
    list = SubmissionArtifactListItem
    get = SubmissionArtifactDetail
    create = SubmissionArtifactCreate
    update = SubmissionArtifactUpdate
    query = SubmissionArtifactQuery
    search = submission_artifact_search



# ===============================
# SubmissionGrade DTOs
# ===============================

class SubmissionGradeCreate(BaseModel):
    """DTO for creating submission grades."""
    artifact_id: UUID
    graded_by_course_member_id: UUID
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
    id: UUID
    artifact_id: UUID
    graded_by_course_member_id: UUID
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
    id: Optional[UUID] = None
    artifact_id: Optional[UUID] = None
    graded_by_course_member_id: Optional[UUID] = None
    status: Optional[GradingStatus] = None


def submission_grade_search(db: Session, query, params: SubmissionGradeQuery):
    """Apply filters for submission grade listings."""
    if params.id is not None:
        query = query.filter(SubmissionGrade.id == params.id)
    if params.artifact_id is not None:
        query = query.filter(SubmissionGrade.artifact_id == params.artifact_id)
    if params.graded_by_course_member_id is not None:
        query = query.filter(SubmissionGrade.graded_by_course_member_id == params.graded_by_course_member_id)
    if params.status is not None:
        query = query.filter(SubmissionGrade.status == params.status.value)

    return query.order_by(SubmissionGrade.graded_at.desc())


class SubmissionGradeInterface(EntityInterface):
    """Entity interface for submission grades."""
    model = SubmissionGrade
    list = SubmissionGradeListItem
    get = SubmissionGradeDetail
    create = SubmissionGradeCreate
    update = SubmissionGradeUpdate
    query = SubmissionGradeQuery
    search = submission_grade_search


# ===============================
# SubmissionReview DTOs
# ===============================

class SubmissionReviewCreate(BaseModel):
    """DTO for creating submission reviews."""
    artifact_id: UUID
    reviewer_course_member_id: UUID
    body: str
    review_type: Optional[str] = None


class SubmissionReviewUpdate(BaseModel):
    """DTO for updating submission reviews."""
    body: Optional[str] = None
    review_type: Optional[str] = None


class SubmissionReviewListItem(BaseEntityList):
    """List item representation for submission reviews."""
    id: UUID
    artifact_id: UUID
    reviewer_course_member_id: UUID
    body: str
    review_type: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubmissionReviewDetail(SubmissionReviewListItem):
    """Detailed view of submission review."""
    pass  # Same as list item for now


class SubmissionReviewQuery(ListQuery):
    """Query parameters for listing submission reviews."""
    id: Optional[UUID] = None
    artifact_id: Optional[UUID] = None
    reviewer_course_member_id: Optional[UUID] = None
    review_type: Optional[str] = None


def submission_review_search(db: Session, query, params: SubmissionReviewQuery):
    """Apply filters for submission review listings."""
    if params.id is not None:
        query = query.filter(SubmissionReview.id == params.id)
    if params.artifact_id is not None:
        query = query.filter(SubmissionReview.artifact_id == params.artifact_id)
    if params.reviewer_course_member_id is not None:
        query = query.filter(SubmissionReview.reviewer_course_member_id == params.reviewer_course_member_id)
    if params.review_type is not None:
        query = query.filter(SubmissionReview.review_type == params.review_type)

    return query.order_by(SubmissionReview.created_at.desc())


class SubmissionReviewInterface(EntityInterface):
    """Entity interface for submission reviews."""
    model = SubmissionReview
    list = SubmissionReviewListItem
    get = SubmissionReviewDetail
    create = SubmissionReviewCreate
    update = SubmissionReviewUpdate
    query = SubmissionReviewQuery
    search = submission_review_search


# ===============================
# ResultArtifact DTOs
# ===============================

class ResultArtifactCreate(BaseModel):
    """DTO for creating result artifacts."""
    result_id: UUID
    content_type: Optional[str] = None
    file_size: int
    bucket_name: str
    object_key: str
    properties: Optional[dict[str, Any]] = None


class ResultArtifactListItem(BaseEntityList):
    """List item representation for result artifacts."""
    id: UUID
    result_id: UUID
    content_type: Optional[str] = None
    file_size: int
    bucket_name: str
    object_key: str
    created_at: datetime
    properties: Optional[dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class ResultArtifactQuery(ListQuery):
    """Query parameters for listing result artifacts."""
    id: Optional[UUID] = None
    result_id: Optional[UUID] = None
    content_type: Optional[str] = None


def result_artifact_search(db: Session, query, params: ResultArtifactQuery):
    """Apply filters for result artifact listings."""
    if params.id is not None:
        query = query.filter(ResultArtifact.id == params.id)
    if params.result_id is not None:
        query = query.filter(ResultArtifact.result_id == params.result_id)
    if params.content_type is not None:
        query = query.filter(ResultArtifact.content_type == params.content_type)

    return query.order_by(ResultArtifact.created_at.desc())


class ResultArtifactInterface(EntityInterface):
    """Entity interface for result artifacts."""
    model = ResultArtifact
    list = ResultArtifactListItem
    get = ResultArtifactListItem
    create = ResultArtifactCreate
    query = ResultArtifactQuery
    search = result_artifact_search