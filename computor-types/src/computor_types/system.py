"""
System-related DTOs and interfaces.

This module contains Pydantic models for system operations like
releases, status queries, and task management.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from .deployments import ComputorDeploymentConfig
from .courses import CourseUpdate
from .course_content_types import CourseContentTypeCreate
from .users import UserGet

class StudentCreate(BaseModel):
    """DTO for creating a student."""
    user_id: Optional[str | str] = None
    user: Optional[UserGet] = None
    course_group_id: Optional[str | str] = None
    course_group_title: Optional[str] = None
    role: Optional[str] = None

class ReleaseStudentsCreate(BaseModel):
    """DTO for releasing multiple students."""
    students: List[StudentCreate] = []
    course_id: str | str

class TUGStudentExport(BaseModel):
    """DTO for TUG student export data."""
    course_group_title: str
    family_name: str
    given_name: str
    matriculation_number: str
    created_at: str

class ReleaseCourseCreate(BaseModel):
    """DTO for releasing a course."""
    course_id: Optional[str] = None
    gitlab_url: Optional[str] = None
    descendants: Optional[bool] = False
    deployment: Optional[ComputorDeploymentConfig] = None

class ReleaseCourseContentCreate(BaseModel):
    """DTO for releasing course content."""
    release_dir: Optional[str] = None
    course_id: Optional[str] = None
    gitlab_url: Optional[str] = None
    ascendants: bool = False
    descendants: bool = False
    deployment: Optional[ComputorDeploymentConfig] = None

class StatusQuery(BaseModel):
    """DTO for status query parameters."""
    course_id: Optional[str] = None

class CourseReleaseUpdate(BaseModel):
    """DTO for updating course release."""
    course: Optional[CourseUpdate] = None
    course_content_types: List[CourseContentTypeCreate]

class GitLabCredentials(BaseModel):
    """GitLab connection credentials."""
    gitlab_url: str
    gitlab_token: str

class OrganizationTaskRequest(BaseModel):
    """Request to create an organization via Temporal workflow."""
    organization: Dict  # OrganizationCreate data
    gitlab: GitLabCredentials
    parent_group_id: int

class CourseFamilyTaskRequest(BaseModel):
    """Request to create a course family via Temporal workflow."""
    course_family: Dict  # CourseFamilyCreate data
    organization_id: str
    gitlab: Optional[GitLabCredentials] = None  # Optional - will use org's GitLab config if not provided

class CourseTaskRequest(BaseModel):
    """Request to create a course via Temporal workflow."""
    course: Dict  # CourseCreate data
    course_family_id: str
    gitlab: Optional[GitLabCredentials] = None  # Optional - will use course family's GitLab config if not provided

class TaskResponse(BaseModel):
    """Response with task ID for async operation."""
    task_id: str
    status: str
    message: str

class PendingChange(BaseModel):
    """Represents a pending change for template generation."""
    type: str = Field(description="new, update, remove")
    content_id: str
    path: str
    title: str

class PendingChangesResponse(BaseModel):
    """Response for pending changes check."""
    total_changes: int
    changes: List[PendingChange]
    last_release: Optional[Dict[str, Any]] = None

class ReleaseOverride(BaseModel):
    """Per-item override for release commit selection."""
    course_content_id: str | str
    version_identifier: str = Field(description="Commit SHA to use for this content")

class ReleaseSelection(BaseModel):
    """Selection of contents and commits for a release."""
    # Selection scope
    course_content_ids: Optional[List[str | str]] = Field(
        default=None,
        description="Explicit list of course content IDs to release"
    )
    parent_id: Optional[str | str] = Field(
        default=None,
        description="Parent content ID; combined with include_descendants"
    )
    include_descendants: bool = Field(
        default=True,
        description="Whether to include descendants of parent_id"
    )
    all: bool = Field(
        default=False,
        description="Select all contents in the course"
    )

    # Commit selection
    global_commit: Optional[str] = Field(
        default=None,
        description="Commit SHA to apply to all selected contents (overridden by per-item overrides)"
    )
    overrides: Optional[List[ReleaseOverride]] = Field(
        default=None,
        description="Per-content commit overrides"
    )

class GenerateTemplateRequest(BaseModel):
    """Request to generate student template."""
    commit_message: Optional[str] = Field(
        default=None,
        description="Custom commit message (optional)"
    )
    force_redeploy: bool = Field(
        default=False,
        description="Force redeployment of already deployed content"
    )
    release: Optional[ReleaseSelection] = Field(
        default=None,
        description="Selection of contents and commits to release"
    )

class GenerateTemplateResponse(BaseModel):
    """Response for template generation request."""
    workflow_id: str
    status: str = "started"
    contents_to_process: int

class BulkAssignExamplesRequest(BaseModel):
    """Request to assign multiple examples to course contents."""
    assignments: List[Dict[str, str]] = Field(
        description="List of assignments with course_content_id, example_id, and example_version"
    )

class GenerateAssignmentsRequest(BaseModel):
    """Request to generate the assignments repository from Example Library."""
    assignments_url: Optional[str] = Field(default=None)
    course_content_ids: Optional[List[str]] = None
    parent_id: Optional[str] = None
    include_descendants: bool = True
    all: bool = False
    overwrite_strategy: str = Field(default="skip_if_exists", description="skip_if_exists|force_update")
    commit_message: Optional[str] = None

class GenerateAssignmentsResponse(BaseModel):
    workflow_id: str
    status: str = "started"
    contents_to_process: int
