"""
Pydantic schemas for Coder API integration.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field


class WorkspaceTemplate(str, Enum):
    """Available workspace templates."""

    PYTHON = "python3.13-workspace"
    MATLAB = "matlab-workspace"


class WorkspaceStatus(str, Enum):
    """Workspace status from Coder API."""

    PENDING = "pending"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    CANCELING = "canceling"
    CANCELED = "canceled"
    DELETING = "deleting"
    DELETED = "deleted"


class WorkspaceBuildStatus(str, Enum):
    """Workspace build status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


# Request schemas

class CoderUserCreate(BaseModel):
    """Schema for creating a Coder user."""

    username: str = Field(..., min_length=1, max_length=100, description="Unique username")
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="User password")
    full_name: Optional[str] = Field(None, max_length=200, description="Display name")


class CoderWorkspaceCreate(BaseModel):
    """Schema for creating a Coder workspace."""

    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Workspace name (defaults to {username}-workspace)"
    )
    template: WorkspaceTemplate = Field(
        WorkspaceTemplate.PYTHON,
        description="Workspace template to use"
    )
    code_server_password: Optional[str] = Field(
        None,
        description="Password for direct code-server access"
    )


class WorkspaceProvisionRequest(BaseModel):
    """Request to provision a workspace for a user."""

    password: str = Field(
        ...,
        min_length=6,
        description="User's password (required for Coder user creation)"
    )
    template: WorkspaceTemplate = Field(
        WorkspaceTemplate.PYTHON,
        description="Workspace template to use"
    )
    workspace_name: Optional[str] = Field(
        None,
        description="Custom workspace name (defaults to {username}-workspace)"
    )


# Response schemas

class CoderUser(BaseModel):
    """Coder user information."""

    id: str = Field(..., description="Coder user ID (UUID)")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    name: Optional[str] = Field(None, description="Display name")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    status: Optional[str] = Field(None, description="User status")


class CoderWorkspace(BaseModel):
    """Coder workspace information."""

    id: str = Field(..., description="Workspace ID (UUID)")
    name: str = Field(..., description="Workspace name")
    owner_id: str = Field(..., description="Owner user ID")
    owner_name: Optional[str] = Field(None, description="Owner username")
    template_id: str = Field(..., description="Template ID")
    template_name: Optional[str] = Field(None, description="Template name")
    latest_build_status: Optional[WorkspaceBuildStatus] = Field(
        None,
        description="Latest build status"
    )
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class WorkspaceDetails(BaseModel):
    """Detailed workspace information including access URLs."""

    workspace: CoderWorkspace = Field(..., description="Workspace info")
    status: WorkspaceStatus = Field(..., description="Current workspace status")
    access_url: Optional[str] = Field(None, description="Direct workspace access URL")
    code_server_url: Optional[str] = Field(None, description="Code-server URL")
    health: Optional[str] = Field(None, description="Workspace health status")
    resources: Optional[dict[str, Any]] = Field(None, description="Workspace resources")


class ProvisionResult(BaseModel):
    """Result of user/workspace provisioning."""

    user: CoderUser = Field(..., description="Created or existing Coder user")
    workspace: Optional[CoderWorkspace] = Field(None, description="Created workspace")
    created_user: bool = Field(False, description="Whether user was newly created")
    created_workspace: bool = Field(False, description="Whether workspace was newly created")
    code_server_password: Optional[str] = Field(
        None,
        description="Code-server password (only returned on creation)"
    )


class CoderTemplate(BaseModel):
    """Coder template information."""

    id: str = Field(..., description="Template ID")
    name: str = Field(..., description="Template name")
    display_name: Optional[str] = Field(None, description="Display name")
    description: Optional[str] = Field(None, description="Template description")
    icon: Optional[str] = Field(None, description="Template icon URL")
    active_version_id: Optional[str] = Field(None, description="Active version ID")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")


class WorkspaceListResponse(BaseModel):
    """Response for listing workspaces."""

    workspaces: list[CoderWorkspace] = Field(default_factory=list)
    count: int = Field(0, description="Total count")


class TemplateListResponse(BaseModel):
    """Response for listing templates."""

    templates: list[CoderTemplate] = Field(default_factory=list)
    count: int = Field(0, description="Total count")


class WorkspaceActionResponse(BaseModel):
    """Response for workspace actions (start/stop/delete)."""

    success: bool = Field(..., description="Whether action was successful")
    message: str = Field(..., description="Status message")
    workspace_id: Optional[str] = Field(None, description="Workspace ID")
    new_status: Optional[WorkspaceStatus] = Field(None, description="New workspace status")


class CoderHealthResponse(BaseModel):
    """Coder server health check response."""

    healthy: bool = Field(..., description="Whether Coder is healthy")
    version: Optional[str] = Field(None, description="Coder version")
    message: Optional[str] = Field(None, description="Status message")
