"""Schemas for workspace role management and provisioning."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class WorkspaceRoleUser(BaseModel):
    """A user with their workspace roles."""
    user_id: str
    email: str | None
    username: str | None
    given_name: str | None
    family_name: str | None
    roles: list[str] = Field(default_factory=list)


class WorkspaceRoleAssign(BaseModel):
    """Request to assign a workspace role by email."""
    email: str
    role_id: str


class WorkspaceTemplate(str, Enum):
    """Available workspace templates."""
    PYTHON = "python-workspace"
    MATLAB = "matlab-workspace"


class WorkspaceProvisionRequest(BaseModel):
    """Request to provision a workspace."""
    email: Optional[str] = Field(None, description="Target user email. If omitted, provisions for the current user.")
    template: WorkspaceTemplate = Field(WorkspaceTemplate.PYTHON, description="Workspace template to use")
    workspace_name: Optional[str] = Field(None, description="Custom workspace name")
