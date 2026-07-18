"""Client-facing DTOs for course-scoped workspace configuration.

A course may allow a set of Coder workspace templates (join table
``course_workspace_template``) plus a ``lecturer_provision_enabled`` flag
(``course_workspace_settings``). Both are governed by workspace maintainers
(``workspace:manage``); course members read the config to render launch
buttons, lecturers use it to bulk-provision throwaway workspaces.

Plain response models (not registered CRUD entities).
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from computor_types.coder import CoderTemplate, CoderWorkspace


class CourseWorkspaceTemplateItem(BaseModel):
    """One template allowed in a course, enriched from Coder best-effort."""

    template_name: str = Field(..., description="Coder template name (e.g. 'vscode-workspace')")
    enabled: bool = Field(
        True, description="Global enable state (a template without a settings row is enabled)"
    )
    display_name: Optional[str] = Field(None, description="Coder display name (None when Coder unreachable)")
    description: Optional[str] = Field(None, description="Coder template description")
    icon: Optional[str] = Field(None, description="Coder template icon URL/path")
    exists_in_coder: Optional[bool] = Field(
        None, description="Whether Coder currently has this template; None when Coder was unreachable"
    )


class CourseWorkspaceSettingsGet(BaseModel):
    """A course's workspace configuration.

    Non-managers only see globally enabled templates; ``available`` (the
    picker source for the admin UI) is present for managers only.
    """

    course_id: str
    templates: List[CourseWorkspaceTemplateItem] = Field(default_factory=list)
    lecturer_provision_enabled: bool = Field(
        False, description="Whether course lecturers may bulk-provision workspaces for students"
    )
    available: Optional[List[CoderTemplate]] = Field(
        None, description="Managers only: globally enabled Coder templates to pick from"
    )
    can_manage: bool = Field(False, description="Whether the caller may PUT this configuration")


class CourseWorkspaceSettingsUpdate(BaseModel):
    """Replace-list payload for a course's workspace configuration (workspace:manage)."""

    template_names: List[str] = Field(
        default_factory=list, description="Allowed Coder template names (full replacement)"
    )
    lecturer_provision_enabled: bool = Field(False)


class CourseWorkspaceAdminItem(BaseModel):
    """One course row in the workspace-admin Courses view."""

    course_id: str
    title: Optional[str] = None
    path: Optional[str] = None
    template_names: List[str] = Field(default_factory=list)
    lecturer_provision_enabled: bool = False


class CourseWorkspaceAdminListResponse(BaseModel):
    """All courses with their workspace configuration (workspace:manage)."""

    courses: List[CourseWorkspaceAdminItem] = Field(default_factory=list)


class StudentWorkspaceProvisionRequest(BaseModel):
    """Lecturer request to provision workspaces for selected course members."""

    template_name: str = Field(..., description="Course-allowed Coder template name")
    course_member_ids: List[str] = Field(..., description="Course members to provision for")
    home_mode: Literal["shared", "scratch"] = Field(
        "scratch",
        description="'scratch' = throwaway per-workspace home volume (deleted with the "
                    "workspace); 'shared' = the student's usual home volume",
    )
    label: Optional[str] = Field(
        None,
        max_length=32,
        description="Optional name suffix (e.g. 'exam1') so the workspace name cannot "
                    "collide with the student's self-provisioned one; defaults to 'tmp'",
    )


class StudentWorkspaceProvisionOutcome(BaseModel):
    """Per-student result of a bulk provisioning run."""

    course_member_id: str
    user_id: Optional[str] = None
    full_name: Optional[str] = None
    workspace_name: Optional[str] = None
    success: bool = False
    error: Optional[str] = Field(None, description="Failure reason; None on success")


class StudentWorkspaceProvisionResponse(BaseModel):
    """Bulk provisioning outcomes (the batch never aborts on a single failure)."""

    outcomes: List[StudentWorkspaceProvisionOutcome] = Field(default_factory=list)
    succeeded: int = 0
    failed: int = 0


class CourseStudentWorkspaceEntry(BaseModel):
    """A course member together with their course-relevant workspaces."""

    course_member_id: str
    user_id: str
    full_name: Optional[str] = None
    workspaces: List[CoderWorkspace] = Field(default_factory=list)


class CourseStudentWorkspacesResponse(BaseModel):
    """Lecturer view: workspaces of course members using course-allowed templates."""

    students: List[CourseStudentWorkspaceEntry] = Field(default_factory=list)
    count: int = 0
