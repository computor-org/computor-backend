"""
Course member gradings DTOs for progress and grading statistics.

This module provides DTOs for calculating and returning aggregated progress
statistics for course members, including hierarchical aggregation by ltree path
and breakdown by course content type.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List

from computor_types.base import EntityInterface, ListQuery


class ContentTypeGradingStats(BaseModel):
    """Grading statistics for a specific course_content_type."""

    course_content_type_id: str
    course_content_type_slug: str = Field(
        description="Slug of the content type (e.g., 'mandatory', 'optional')"
    )
    course_content_type_title: Optional[str] = None
    course_content_type_color: Optional[str] = None

    max_assignments: int = Field(
        description="Total number of submittable course_contents of this type"
    )
    submitted_assignments: int = Field(
        description="Number of course_contents with at least one SubmissionArtifact.submit=True"
    )
    progress_percentage: float = Field(
        ge=0.0,
        le=100.0,
        description="Progress percentage (submitted/max * 100)"
    )
    latest_submission_at: Optional[datetime] = Field(
        None,
        description="Most recent SubmissionArtifact.created_at with submit=True for this type"
    )

    model_config = ConfigDict(from_attributes=True)


class CourseMemberGradingNode(BaseModel):
    """Aggregated grading data for one ltree path layer.

    Represents a node in the course content hierarchy (e.g., a module, unit, etc.)
    with aggregated submission statistics for all submittable content at or below
    this path level.
    """

    path: str = Field(
        description="The ltree path (e.g., 'module1', 'module1.unit1')"
    )
    title: Optional[str] = Field(
        None,
        description="CourseContent title if a course_content exists at this exact path"
    )

    # Whether this node is submittable (True for assignments, False for units/containers)
    submittable: Optional[bool] = Field(
        None,
        description="Whether this node itself is submittable (True for assignments, False for units)"
    )
    position: Optional[int] = Field(
        None,
        description="Position/order of this content within its parent"
    )
    course_content_type_color: Optional[str] = Field(
        None,
        description="Color of the course content type (hex)"
    )

    # Per course_content_type aggregation
    by_content_type: List[ContentTypeGradingStats] = Field(
        default_factory=list,
        description="Breakdown of statistics by course_content_type"
    )

    # Overall totals (all content types combined)
    max_assignments: int = Field(
        description="Total submittable course_contents at or under this path"
    )
    submitted_assignments: int = Field(
        description="Course_contents with at least one SubmissionArtifact.submit=True"
    )

    # Calculated fields
    progress_percentage: float = Field(
        ge=0.0,
        le=100.0,
        description="Progress percentage (submitted/max * 100)"
    )

    # Latest submission info
    latest_submission_at: Optional[datetime] = Field(
        None,
        description="Most recent SubmissionArtifact.created_at with submit=True under this path"
    )

    model_config = ConfigDict(from_attributes=True)


class CourseMemberGradingsGet(BaseModel):
    """Full response for course member gradings.

    Contains overall course-level statistics, breakdown by content type,
    and hierarchical breakdown by ltree path.
    """

    course_member_id: str
    course_id: str

    # Root level stats (whole course)
    total_max_assignments: int = Field(
        description="Total number of submittable course_contents in the course"
    )
    total_submitted_assignments: int = Field(
        description="Total course_contents with at least one submitted artifact"
    )
    overall_progress_percentage: float = Field(
        ge=0.0,
        le=100.0,
        description="Overall progress percentage for the course"
    )
    latest_submission_at: Optional[datetime] = Field(
        None,
        description="Most recent submission across all content"
    )

    # Per content type totals at course level
    by_content_type: List[ContentTypeGradingStats] = Field(
        default_factory=list,
        description="Course-level breakdown by content type"
    )

    # Hierarchical breakdown by ltree path
    nodes: List[CourseMemberGradingNode] = Field(
        default_factory=list,
        description="Hierarchical breakdown by ltree path levels"
    )

    model_config = ConfigDict(from_attributes=True)


class CourseMemberGradingsList(BaseModel):
    """List item for course member gradings (without hierarchical nodes for efficiency).

    Used when listing all course members' gradings for a course.
    Contains only course-level totals, not the full hierarchical breakdown.
    """

    course_member_id: str
    course_id: str

    # User info for display
    user_id: Optional[str] = None
    username: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None

    # Root level stats (whole course)
    total_max_assignments: int = Field(
        description="Total number of submittable course_contents in the course"
    )
    total_submitted_assignments: int = Field(
        description="Total course_contents with at least one submitted artifact"
    )
    overall_progress_percentage: float = Field(
        ge=0.0,
        le=100.0,
        description="Overall progress percentage for the course"
    )
    latest_submission_at: Optional[datetime] = Field(
        None,
        description="Most recent submission across all content"
    )

    # Per content type totals at course level
    by_content_type: List[ContentTypeGradingStats] = Field(
        default_factory=list,
        description="Course-level breakdown by content type"
    )

    model_config = ConfigDict(from_attributes=True)


class CourseMemberGradingsQuery(ListQuery):
    """Query parameters for course member gradings endpoint."""

    course_id: Optional[str] = Field(
        None,
        description="Filter by course ID (required for list endpoint)"
    )

    model_config = ConfigDict(from_attributes=True)


class CourseMemberGradingsInterface(EntityInterface):
    """Interface for course member gradings.

    This is a read-only interface (no create/update operations) that provides
    aggregated progress statistics for course members.
    """

    # No create/update - this is a read-only aggregation endpoint
    create = None
    update = None

    # Read operations
    get = CourseMemberGradingsGet
    list = CourseMemberGradingsList
    query = CourseMemberGradingsQuery
