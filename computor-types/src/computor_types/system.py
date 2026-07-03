"""
System-related DTOs and interfaces.

This module contains Pydantic models for system operations like
Temporal workflow task requests/responses and template generation.
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field

from computor_types.course_git import CourseGitBindingUpsert


class CourseTaskRequest(BaseModel):
    """Request to create a course via Temporal workflow."""
    course: Dict
    course_family_id: str
    git: Optional[CourseGitBindingUpsert] = Field(
        None,
        description=(
            "Course-level git binding applied at creation: the registry git server "
            "(git_server_id) hosting the student-template, delivery mode, and allowed "
            "student-repo modes. Omit to create the course unbound and configure git "
            "later via the course's git binding. Git is per-course — not inherited "
            "from the organization or course family."
        ),
    )


class TaskResponse(BaseModel):
    """Response with task ID for async operation."""
    task_id: str
    status: str
    message: str


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


class GenerateAssignmentsRequest(BaseModel):
    """Request to generate the assignments repository from Example Library."""
    assignments_url: Optional[str] = Field(default=None)
    course_content_ids: Optional[List[str]] = None
    parent_id: Optional[str] = None
    include_descendants: bool = True
    all: bool = False
    overwrite_strategy: str = Field(default="force_update", description="skip_if_exists|force_update")
    commit_message: Optional[str] = None


class GenerateAssignmentsResponse(BaseModel):
    workflow_id: str
    status: str = "started"
    contents_to_process: int
