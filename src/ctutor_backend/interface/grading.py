from datetime import datetime
from enum import IntEnum
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_
from ctutor_backend.interface.base import EntityInterface, ListQuery, BaseEntityGet
from ctutor_backend.model.course import CourseMember
from ctutor_backend.model.artifact import SubmissionGrade

class GradingAuthor(BaseModel):
    given_name: Optional[str] = Field(None, min_length=1, max_length=255, description="Author's given name")
    family_name: Optional[str] = Field(None, min_length=1, max_length=255, description="Author's family name")

    model_config = ConfigDict(from_attributes=True)

class GradedByCourseMember(BaseModel):
    course_role_id: Optional[str] = None
    user_id: str
    user: Optional[GradingAuthor] = None

    model_config = ConfigDict(from_attributes=True)

class GradingStatus(IntEnum):
    """Enumeration for grading status values."""
    NOT_REVIEWED = 0
    CORRECTED = 1
    CORRECTION_NECESSARY = 2
    IMPROVEMENT_POSSIBLE = 3


class SubmissionGroupGradingCreate(BaseModel):
    """Create a new grading for a submission group."""
    submission_group_id: str
    graded_by_course_member_id: str
    result_id: Optional[str] = None  # Optional reference to the result being graded
    grading: float = Field(ge=0.0, le=1.0)  # Grade between 0.0 and 1.0
    status: GradingStatus = GradingStatus.NOT_REVIEWED
    feedback: Optional[str] = None  # Optional feedback/comments

    graded_by_course_member: Optional[GradedByCourseMember] = Field(
        default=None,
        validation_alias="graded_by",
    )

    model_config = ConfigDict(use_enum_values=True, from_attributes=True)


class SubmissionGroupGradingGet(BaseEntityGet):
    """Full grading information."""
    id: str
    submission_group_id: str
    graded_by_course_member_id: str
    result_id: Optional[str] = None
    grading: float
    status: GradingStatus
    feedback: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    graded_by_course_member: Optional[GradedByCourseMember] = Field(
        default=None,
        validation_alias="graded_by",
    )

    model_config = ConfigDict(use_enum_values=True, from_attributes=True)


class SubmissionGroupGradingList(BaseModel):
    """List view of grading."""
    id: str
    submission_group_id: str
    graded_by_course_member_id: str
    result_id: Optional[str] = None
    grading: float
    status: GradingStatus
    feedback: Optional[str] = None
    created_at: datetime
    graded_by_course_member: Optional[GradedByCourseMember] = None

    model_config = ConfigDict(use_enum_values=True, from_attributes=True, populate_by_name=True)


class SubmissionGroupGradingUpdate(BaseModel):
    """Update grading information."""
    grading: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    status: Optional[GradingStatus] = None
    feedback: Optional[str] = None
    result_id: Optional[str] = None
    
    model_config = ConfigDict(use_enum_values=True, from_attributes=True)


class SubmissionGroupGradingQuery(ListQuery):
    """Query parameters for searching gradings."""
    id: Optional[str] = None
    submission_group_id: Optional[str] = None
    graded_by_course_member_id: Optional[str] = None
    result_id: Optional[str] = None
    status: Optional[GradingStatus] = None
    min_grade: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    max_grade: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    has_feedback: Optional[bool] = None
    
    model_config = ConfigDict(use_enum_values=True, from_attributes=True)


def grading_search(db: Session, query, params: Optional[SubmissionGroupGradingQuery]):
    """Search function for gradings.

    TODO: Migrate to use SubmissionGrade from artifact model
    """
    # Temporarily disabled - needs migration to new artifact-based system
    return query.filter(False)  # Return empty result

    # Original code commented out:
    # query = query.options(
    #     joinedload(SubmissionGroupGrading.graded_by).joinedload(CourseMember.user),
    #     joinedload(SubmissionGroupGrading.graded_by).joinedload(CourseMember.course_role),
    # )
    # if params.id is not None:
    #     query = query.filter(SubmissionGroupGrading.id == params.id)
    # Commented out rest of function - needs migration
    # if params.submission_group_id is not None:
    #     query = query.filter(SubmissionGroupGrading.submission_group_id == params.submission_group_id)
    # ... rest of filters
    # return query


# TODO: Migrate this interface to use SubmissionGrade from artifact model
class SubmissionGroupGradingInterface(EntityInterface):
    create = SubmissionGroupGradingCreate
    get = SubmissionGroupGradingGet
    list = SubmissionGroupGradingList
    update = SubmissionGroupGradingUpdate
    query = SubmissionGroupGradingQuery
    search = grading_search
    endpoint = "submission-group-gradings"
    model = SubmissionGrade  # Changed to use new model
    cache_ttl = 60  # 1 minute - gradings may change frequently


# Student-friendly grading view (simplified, read-only)
class GradingStudentView(BaseModel):
    """Simplified grading view for students."""
    id: str
    grading: float
    status: GradingStatus
    feedback: Optional[str] = None
    graded_by_name: Optional[str] = None  # Name of the grader (not ID)
    graded_at: datetime  # When the grading was done
    
    model_config = ConfigDict(use_enum_values=True, from_attributes=True)


# Tutor/Lecturer grading summary
class GradingSummary(BaseModel):
    """Summary of gradings for a course content."""
    course_content_id: str
    total_submissions: int
    graded_count: int
    ungraded_count: int
    corrected_count: int
    correction_necessary_count: int
    improvement_possible_count: int
    average_grade: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)
