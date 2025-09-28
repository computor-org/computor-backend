"""Pydantic DTOs for artifact-related models."""
from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.orm import Session

from ctutor_backend.interface.base import BaseEntityList, EntityInterface, ListQuery
from ctutor_backend.interface.tasks import TaskStatus, map_int_to_task_status
from ctutor_backend.model.artifact import SubmissionArtifact, ResultArtifact, TestResult, ArtifactGrade, ArtifactReview


# ===============================
# SubmissionArtifact DTOs
# ===============================

class SubmissionArtifactCreate(BaseModel):
    """DTO for creating submission artifacts."""
    submission_group_id: UUID
    filename: str
    original_filename: Optional[str] = None
    content_type: Optional[str] = None
    file_size: int
    bucket_name: str
    object_key: str
    properties: Optional[dict[str, Any]] = None


class SubmissionArtifactUpdate(BaseModel):
    """DTO for updating submission artifacts."""
    filename: Optional[str] = None
    properties: Optional[dict[str, Any]] = None


class SubmissionArtifactListItem(BaseEntityList):
    """List item representation for submission artifacts."""
    id: UUID
    submission_group_id: UUID
    uploaded_by_course_member_id: Optional[UUID] = None
    filename: str
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
    latest_test_result: Optional['TestResultListItem'] = None
    average_grade: Optional[float] = None


class SubmissionArtifactQuery(ListQuery):
    """Query parameters for listing submission artifacts."""
    id: Optional[UUID] = None
    submission_group_id: Optional[UUID] = None
    uploaded_by_course_member_id: Optional[UUID] = None
    filename: Optional[str] = None
    content_type: Optional[str] = None


def submission_artifact_search(db: Session, query, params: SubmissionArtifactQuery):
    """Apply filters for submission artifact listings."""
    if params.id is not None:
        query = query.filter(SubmissionArtifact.id == params.id)
    if params.submission_group_id is not None:
        query = query.filter(SubmissionArtifact.submission_group_id == params.submission_group_id)
    if params.uploaded_by_course_member_id is not None:
        query = query.filter(SubmissionArtifact.uploaded_by_course_member_id == params.uploaded_by_course_member_id)
    if params.filename is not None:
        query = query.filter(SubmissionArtifact.filename.ilike(f"%{params.filename}%"))
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
# TestResult DTOs
# ===============================

class TestResultCreate(BaseModel):
    """DTO for creating test results."""
    submission_artifact_id: UUID
    course_member_id: UUID
    execution_backend_id: Optional[UUID] = None
    test_system_id: Optional[str] = None
    status: TaskStatus
    score: float = 0.0
    max_score: Optional[float] = None
    result_json: Optional[dict[str, Any]] = None
    properties: Optional[dict[str, Any]] = None
    log_text: Optional[str] = None
    version_identifier: Optional[str] = None
    reference_version_identifier: Optional[str] = None


class TestResultUpdate(BaseModel):
    """DTO for updating test results."""
    status: Optional[TaskStatus] = None
    score: Optional[float] = None
    max_score: Optional[float] = None
    result_json: Optional[dict[str, Any]] = None
    properties: Optional[dict[str, Any]] = None
    log_text: Optional[str] = None
    finished_at: Optional[datetime] = None


class TestResultListItem(BaseEntityList):
    """List item representation for test results."""
    id: UUID
    submission_artifact_id: UUID
    course_member_id: UUID
    execution_backend_id: Optional[UUID] = None
    test_system_id: Optional[str] = None
    status: TaskStatus
    score: float
    max_score: Optional[float] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    version_identifier: Optional[str] = None
    reference_version_identifier: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("status", mode="before")
    @classmethod
    def _coerce_status(cls, value):
        if isinstance(value, TaskStatus):
            return value
        return map_int_to_task_status(value)


class TestResultDetail(TestResultListItem):
    """Detailed view of test result with full data."""
    result_json: Optional[dict[str, Any]] = None
    properties: Optional[dict[str, Any]] = None
    log_text: Optional[str] = None
    result_artifacts_count: Optional[int] = None


class TestResultQuery(ListQuery):
    """Query parameters for listing test results."""
    id: Optional[UUID] = None
    submission_artifact_id: Optional[UUID] = None
    course_member_id: Optional[UUID] = None
    execution_backend_id: Optional[UUID] = None
    test_system_id: Optional[str] = None
    status: Optional[TaskStatus] = None


def test_result_search(db: Session, query, params: TestResultQuery):
    """Apply filters for test result listings."""
    if params.id is not None:
        query = query.filter(TestResult.id == params.id)
    if params.submission_artifact_id is not None:
        query = query.filter(TestResult.submission_artifact_id == params.submission_artifact_id)
    if params.course_member_id is not None:
        query = query.filter(TestResult.course_member_id == params.course_member_id)
    if params.execution_backend_id is not None:
        query = query.filter(TestResult.execution_backend_id == params.execution_backend_id)
    if params.test_system_id is not None:
        query = query.filter(TestResult.test_system_id == params.test_system_id)
    if params.status is not None:
        from ctutor_backend.interface.tasks import map_task_status_to_int
        query = query.filter(TestResult.status == map_task_status_to_int(params.status))

    return query.order_by(TestResult.created_at.desc())


class TestResultInterface(EntityInterface):
    """Entity interface for test results."""
    model = TestResult
    list = TestResultListItem
    get = TestResultDetail
    create = TestResultCreate
    update = TestResultUpdate
    query = TestResultQuery
    search = test_result_search


# ===============================
# ArtifactGrade DTOs
# ===============================

class ArtifactGradeCreate(BaseModel):
    """DTO for creating artifact grades."""
    artifact_id: UUID
    graded_by_course_member_id: UUID
    score: float
    max_score: float
    rubric: Optional[dict[str, Any]] = None
    comment: Optional[str] = None


class ArtifactGradeUpdate(BaseModel):
    """DTO for updating artifact grades."""
    score: Optional[float] = None
    max_score: Optional[float] = None
    rubric: Optional[dict[str, Any]] = None
    comment: Optional[str] = None


class ArtifactGradeListItem(BaseEntityList):
    """List item representation for artifact grades."""
    id: UUID
    artifact_id: UUID
    graded_by_course_member_id: UUID
    score: float
    max_score: float
    comment: Optional[str] = None
    graded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ArtifactGradeDetail(ArtifactGradeListItem):
    """Detailed view of artifact grade."""
    rubric: Optional[dict[str, Any]] = None


class ArtifactGradeQuery(ListQuery):
    """Query parameters for listing artifact grades."""
    id: Optional[UUID] = None
    artifact_id: Optional[UUID] = None
    graded_by_course_member_id: Optional[UUID] = None


def artifact_grade_search(db: Session, query, params: ArtifactGradeQuery):
    """Apply filters for artifact grade listings."""
    if params.id is not None:
        query = query.filter(ArtifactGrade.id == params.id)
    if params.artifact_id is not None:
        query = query.filter(ArtifactGrade.artifact_id == params.artifact_id)
    if params.graded_by_course_member_id is not None:
        query = query.filter(ArtifactGrade.graded_by_course_member_id == params.graded_by_course_member_id)

    return query.order_by(ArtifactGrade.graded_at.desc())


class ArtifactGradeInterface(EntityInterface):
    """Entity interface for artifact grades."""
    model = ArtifactGrade
    list = ArtifactGradeListItem
    get = ArtifactGradeDetail
    create = ArtifactGradeCreate
    update = ArtifactGradeUpdate
    query = ArtifactGradeQuery
    search = artifact_grade_search


# ===============================
# ArtifactReview DTOs
# ===============================

class ArtifactReviewCreate(BaseModel):
    """DTO for creating artifact reviews."""
    artifact_id: UUID
    reviewer_course_member_id: UUID
    body: str
    review_type: Optional[str] = None


class ArtifactReviewUpdate(BaseModel):
    """DTO for updating artifact reviews."""
    body: Optional[str] = None
    review_type: Optional[str] = None


class ArtifactReviewListItem(BaseEntityList):
    """List item representation for artifact reviews."""
    id: UUID
    artifact_id: UUID
    reviewer_course_member_id: UUID
    body: str
    review_type: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ArtifactReviewDetail(ArtifactReviewListItem):
    """Detailed view of artifact review."""
    pass  # Same as list item for now


class ArtifactReviewQuery(ListQuery):
    """Query parameters for listing artifact reviews."""
    id: Optional[UUID] = None
    artifact_id: Optional[UUID] = None
    reviewer_course_member_id: Optional[UUID] = None
    review_type: Optional[str] = None


def artifact_review_search(db: Session, query, params: ArtifactReviewQuery):
    """Apply filters for artifact review listings."""
    if params.id is not None:
        query = query.filter(ArtifactReview.id == params.id)
    if params.artifact_id is not None:
        query = query.filter(ArtifactReview.artifact_id == params.artifact_id)
    if params.reviewer_course_member_id is not None:
        query = query.filter(ArtifactReview.reviewer_course_member_id == params.reviewer_course_member_id)
    if params.review_type is not None:
        query = query.filter(ArtifactReview.review_type == params.review_type)

    return query.order_by(ArtifactReview.created_at.desc())


class ArtifactReviewInterface(EntityInterface):
    """Entity interface for artifact reviews."""
    model = ArtifactReview
    list = ArtifactReviewListItem
    get = ArtifactReviewDetail
    create = ArtifactReviewCreate
    update = ArtifactReviewUpdate
    query = ArtifactReviewQuery
    search = artifact_review_search


# ===============================
# ResultArtifact DTOs
# ===============================

class ResultArtifactCreate(BaseModel):
    """DTO for creating result artifacts."""
    test_result_id: UUID
    filename: str
    content_type: Optional[str] = None
    file_size: int
    bucket_name: str
    object_key: str
    properties: Optional[dict[str, Any]] = None


class ResultArtifactListItem(BaseEntityList):
    """List item representation for result artifacts."""
    id: UUID
    test_result_id: UUID
    filename: str
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
    test_result_id: Optional[UUID] = None
    filename: Optional[str] = None
    content_type: Optional[str] = None


def result_artifact_search(db: Session, query, params: ResultArtifactQuery):
    """Apply filters for result artifact listings."""
    if params.id is not None:
        query = query.filter(ResultArtifact.id == params.id)
    if params.test_result_id is not None:
        query = query.filter(ResultArtifact.test_result_id == params.test_result_id)
    if params.filename is not None:
        query = query.filter(ResultArtifact.filename.ilike(f"%{params.filename}%"))
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