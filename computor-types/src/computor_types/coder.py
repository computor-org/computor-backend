"""
Pydantic schemas for the Coder workspace API (backend ``/coder`` endpoints).

Moved here from ``computor_backend.coder.schemas`` — API-facing DTOs live in
computor-types; that module remains as a re-export shim.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel, Field

from computor_types.tasks import TaskInfo


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
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELING = "canceling"
    CANCELED = "canceled"
    DELETING = "deleting"


# Request schemas

class CoderUserCreate(BaseModel):
    """Schema for creating a Coder user."""

    username: str = Field(..., min_length=1, max_length=100, description="Unique username")
    email: str = Field(..., description="User email address")  # Changed from EmailStr to str to allow .local domains
    password: str = Field(..., min_length=6, description="User password")
    full_name: Optional[str] = Field(None, max_length=200, description="Display name")


class CoderWorkspaceCreate(BaseModel):
    """Schema for creating a Coder workspace."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Workspace name"
    )
    template: str = Field(
        ...,
        description="Workspace template name (must exist in Coder)"
    )
    code_server_password: Optional[str] = Field(
        None,
        description="Password for direct code-server access"
    )
    computor_auth_token: Optional[str] = Field(
        None,
        description="Pre-minted API token for automatic extension authentication"
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

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "CoderUser":
        """Build a CoderUser from a Coder API user payload."""
        return cls(
            id=data["id"],
            username=data["username"],
            email=data["email"],
            name=data.get("name"),
            created_at=data.get("created_at"),
            status=data.get("status"),
        )


class CoderWorkspace(BaseModel):
    """Coder workspace information."""

    id: str = Field(..., description="Workspace ID (UUID)")
    name: str = Field(..., description="Workspace name")
    owner_id: str = Field(..., description="Owner user ID")
    owner_name: Optional[str] = Field(None, description="Owner username")
    template_id: str = Field(..., description="Template ID")
    template_name: Optional[str] = Field(None, description="Raw template name (stable identifier, e.g. 'python-workspace')")
    template_display_name: Optional[str] = Field(None, description="Human-readable template display name")
    template_version_id: Optional[str] = Field(
        None, description="Template version the latest build ran (for fleet/update views)"
    )
    template_version_name: Optional[str] = Field(
        None, description="Human-readable template version name of the latest build"
    )
    latest_build_transition: Optional[str] = Field(
        None, description="Transition of the latest build: start | stop | delete"
    )
    latest_build_status: Optional[WorkspaceBuildStatus] = Field(
        None,
        description="Latest build status"
    )
    automatic_updates: Optional[str] = Field(
        None,
        description="Coder automatic update policy: always | never",
    )
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class WorkspaceDetails(BaseModel):
    """Detailed workspace information including access URLs."""

    workspace: CoderWorkspace = Field(..., description="Workspace info")
    status: WorkspaceStatus = Field(..., description="Current workspace status")
    access_url: Optional[str] = Field(None, description="Direct workspace access URL")
    code_server_url: Optional[str] = Field(None, description="Code-server URL")
    health: Optional[Union[str, bool]] = Field(None, description="Workspace health status")
    resources: Optional[dict[str, Any]] = Field(None, description="Workspace resources")
    agent_lifecycle: Optional[str] = Field(
        None,
        description=(
            "Coder agent lifecycle_state: created|starting|ready|start_timeout|"
            "start_error|off|shutting_down|shutdown_*. Reports how far the agent's "
            "startup script got, unlike the connection status in `resources`."
        ),
    )
    ready: bool = Field(
        False,
        description=(
            "Workspace is RUNNING and its agent finished its startup script. "
            "RUNNING alone only means the Terraform apply succeeded, so the service "
            "inside may still be booting; prefer this before sending a user to the URL."
        ),
    )


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


class CoderLoginRequest(BaseModel):
    """Request to login to Coder."""

    password: str
    redirect_url: Optional[str] = None


class CoderSessionResponse(BaseModel):
    """Response with Coder session token."""

    success: bool
    session_token: Optional[str] = None
    message: str


# Admin task schemas (image building, template pushing)

class ImageBuildRequest(BaseModel):
    """Request to build workspace Docker images."""

    templates: Optional[list[str]] = Field(
        None,
        description="Template names to build (e.g. ['python3.13', 'matlab']). None = all templates."
    )
    image_tag: Optional[str] = Field(
        None,
        description="Immutable image tag to publish alongside :latest (e.g. 'v20260706-1400'). None = auto-generated from the run time.",
    )


class TemplatePushRequest(BaseModel):
    """Request to push Coder templates (Terraform configs)."""

    templates: Optional[list[str]] = Field(
        None,
        description="Template names to push (e.g. ['python-workspace', 'matlab-workspace']). None = all templates."
    )
    build_images: bool = Field(
        False,
        description="Build workspace images before pushing templates."
    )
    image_tag: Optional[str] = Field(
        None,
        description="Immutable image tag the pushed template version pins to (and builds, when build_images). None = auto-generated from the run time.",
    )


class WorkspaceRolloutRequest(BaseModel):
    """Request to roll existing workspaces onto their template's active version."""

    templates: Optional[list[str]] = Field(
        None,
        description="Template names to roll out (e.g. ['python3.13']). None = all templates."
    )


class CoderAdminTaskResponse(BaseModel):
    """Response for admin task submission."""

    workflow_id: str = Field(..., description="Temporal workflow ID for tracking")
    task_name: str = Field(..., description="Name of the submitted task")
    status: str = Field("submitted", description="Initial task status")


class CoderTemplateFleetStatus(BaseModel):
    """Update readiness for one Coder template."""

    id: str
    name: str
    display_name: Optional[str] = None
    active_version_id: Optional[str] = None
    workspace_count: int = 0
    current_count: int = 0
    outdated_count: int = 0
    running_outdated_count: int = 0
    scheduled_on_start_count: int = 0
    actionable_count: int = 0
    rollout_state: str


class CoderFleetStatusResponse(BaseModel):
    """Privileged template-centric fleet summary."""

    healthy: bool
    version: Optional[str] = None
    templates: list[CoderTemplateFleetStatus] = Field(default_factory=list)
    workspace_count: int = 0


class CoderAdminTaskListResponse(BaseModel):
    """Recent Coder image/template administration workflows."""

    tasks: list[TaskInfo] = Field(default_factory=list)


# Template settings (DB-backed resource limits, quota, variable overrides)

class WorkspaceTemplateSettingsSchema(BaseModel):
    """Per-template settings row (see model.workspace.WorkspaceTemplateSettings)."""

    template_name: str = Field(..., description="Coder template name (e.g. 'vscode-workspace')")
    memory_mb: Optional[int] = Field(
        None, description="Container memory cap in MiB applied at push time; null/0 = unlimited"
    )
    cpu_shares: Optional[int] = Field(
        None, description="Relative CPU weight applied at push time; null/0 = Docker default"
    )
    max_running_workspaces: Optional[int] = Field(
        None,
        description="Max concurrently running workspaces of this template across all "
                    "users; null = unlimited, 0 freezes the template",
    )
    template_variables: dict[str, str] = Field(
        default_factory=dict,
        description="Extra Terraform variable overrides pushed as --variable "
                    "(only to templates that declare them)",
    )
    updated_at: Optional[datetime] = Field(None, description="Last settings change")


class WorkspaceTemplateSettingsUpdate(BaseModel):
    """Upsert payload for a template's settings."""

    memory_mb: Optional[int] = Field(None, ge=0)
    cpu_shares: Optional[int] = Field(
        None, ge=0, description="0 = Docker default; Docker requires values >= 2 otherwise"
    )
    max_running_workspaces: Optional[int] = Field(None, ge=0)
    template_variables: dict[str, str] = Field(default_factory=dict)


class TemplateSettingsListResponse(BaseModel):
    """All stored per-template settings rows."""

    settings: list[WorkspaceTemplateSettingsSchema] = Field(default_factory=list)


# Template file editing (raw) + guided variable editing

class TemplateFile(BaseModel):
    """One editable file of a template directory."""

    name: str
    content: str


class TemplateFilesResponse(BaseModel):
    """Editable files of a deployed template directory."""

    template_name: str = Field(..., description="Coder template name")
    dir_name: str = Field(..., description="Template directory name under the templates root")
    customized: bool = Field(
        ...,
        description="True when the .computor-managed marker is absent: the deployed "
                    "template is operator-customized and no longer auto-synced from the repo",
    )
    files: list[TemplateFile] = Field(default_factory=list)


class TemplateFileUpdateRequest(BaseModel):
    """New content for one template file."""

    content: str


class TemplateFileActionResponse(BaseModel):
    """Result of a template file write / restore-managed action."""

    success: bool
    message: str
    customized: bool


class TemplateVariable(BaseModel):
    """One Terraform variable declared by a template (guided editing surface)."""

    name: str
    type: Optional[str] = Field(None, description="Declared type (string | number | bool | …)")
    default: Optional[Any] = Field(
        None, description="Declared default; masked (null) for sensitive variables"
    )
    has_default: bool = False
    description: Optional[str] = None
    sensitive: bool = False
    managed: bool = Field(
        False,
        description="Supplied by the push pipeline or the settings UI — its file "
                    "default is ignored, so guided editing is locked for it",
    )
    managed_reason: Optional[str] = None
    file: str = Field(..., description="The .tf file declaring this variable")


class TemplateVariablesResponse(BaseModel):
    """Declared variables of a deployed template."""

    template_name: str
    dir_name: str
    customized: bool
    variables: list[TemplateVariable] = Field(default_factory=list)


class TemplateVariableUpdateRequest(BaseModel):
    """Guided edit: new defaults for declared, non-managed variables."""

    defaults: dict[str, Any] = Field(
        ..., description="Variable name → new default value"
    )
