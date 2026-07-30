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
    app_secret: Optional[str] = Field(
        None,
        description="Per-user credential the workspace app requires and the workspace "
                    "ingress injects, so one workspace cannot drive another directly. "
                    "None leaves the app unauthenticated.",
    )
    app_password_hash: Optional[str] = Field(
        None,
        description="Argon2id hash of app_secret, used by the code-server templates as "
                    "HASHED_PASSWORD and as the injected session cookie.",
    )
    computor_auth_token: Optional[str] = Field(
        None,
        description="Pre-minted API token for automatic extension authentication"
    )
    home_mode: Optional[str] = Field(
        None,
        description="Home volume mode: 'shared' (per-user home volume) or "
                    "'scratch' (throwaway per-workspace volume). None = template default (shared).",
    )
    allow_root: Optional[bool] = Field(
        None,
        description="Course-level root policy for this workspace. The template ANDs it with "
                    "its own allow_root, so False always denies but True only permits what "
                    "the template already allows. None = no course-level restriction.",
    )
    allow_internet: Optional[bool] = Field(
        None,
        description="Course-level internet policy for this workspace, ANDed with the "
                    "template's allow_internet the same way. None = no course-level restriction.",
    )
    course_id: Optional[str] = Field(
        None,
        description="Course this workspace is provisioned FOR. None/empty means the user "
                    "provisioned it for themselves, which is what course views scope on: "
                    "without it, a member's personal workspace on a course template is "
                    "indistinguishable from one the course created.",
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
    latest_build_id: Optional[str] = Field(
        None, description="ID of the latest build (for reading its rich parameters)"
    )
    home_mode: Optional[str] = Field(
        None,
        description="Home volume mode ('shared' | 'scratch') read from the latest build's "
                    "rich parameters; only populated by views that need it",
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


class TemplatePreparation(BaseModel):
    """A template an administrator is deploying right now, and how far it got.

    Nothing is deployed automatically, so between an admin picking a template
    and users being able to pick it lies an image build and a push — tens of
    minutes for something like MATLAB. Coder has no such template yet, so it
    cannot appear in a template listing, and a user is left staring at a
    choice that silently lacks the one they were told to use.

    ``status``/``phase`` are the workflow's own pair (see
    tasks/temporal_coder_setup.py), passed through untranslated so the web
    renders them with the same stage vocabulary the administration page uses.
    """

    name: str = Field(..., description="Coder template name (e.g. 'vscode-workspace')")
    display_name: Optional[str] = Field(None, description="Human-readable name")
    description: Optional[str] = Field(None, description="What the template offers")
    icon: Optional[str] = Field(None, description="Coder icon path or absolute URL")
    status: str = Field(
        ..., description="Per-template workflow status: pending | running | succeeded | failed"
    )
    phase: str = Field(
        ..., description="Per-template phase: queued | building | pushing | rolling_out | complete"
    )
    deployed: bool = Field(
        False,
        description="Coder already has this template, so this run is an update and "
                    "the current version stays usable while it runs",
    )
    task_name: str = Field(
        ...,
        description="Workflow behind it: build_workspace_images | push_coder_templates "
                    "| rollout_workspaces",
    )


class TemplateListResponse(BaseModel):
    """Response for listing templates."""

    templates: list[CoderTemplate] = Field(default_factory=list)
    count: int = Field(0, description="Total count")
    preparing: list[TemplatePreparation] = Field(
        default_factory=list,
        description="Templates being deployed right now, with the stage each has "
                    "reached. Scoped exactly like `templates` — a user only ever "
                    "sees the ones they would be allowed to pick.",
    )


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


# Template catalog: what the deployment COULD offer, not just what it does


class TemplateCatalogEntry(BaseModel):
    """One workspace template as it exists on disk, plus its live state.

    The catalog is the union of the template directories shipped with the
    deployment and the templates Coder actually has. A directory that was
    never pushed still appears here (``deployed=False``) — that is the whole
    point: an admin has to be able to see and deploy a template the first
    startup deliberately skipped.
    """

    dir_name: Optional[str] = Field(
        None,
        description="Template directory name (e.g. 'vscode'); null for a "
                    "template that is live in Coder but has no directory here "
                    "(pushed by hand, or its directory was removed) — such a "
                    "template cannot be rebuilt from this deployment.",
    )
    name: str = Field(..., description="Coder template name (e.g. 'vscode-workspace')")
    display_name: Optional[str] = Field(None, description="Human-readable name")
    description: Optional[str] = Field(None, description="What the template offers")
    icon: Optional[str] = Field(None, description="Coder icon path or absolute URL")
    image_name: Optional[str] = Field(None, description="Docker image the template builds")
    deployed: bool = Field(
        False, description="Whether Coder currently has this template"
    )
    template_id: Optional[str] = Field(None, description="Coder template ID when deployed")
    active_version_id: Optional[str] = Field(None, description="Active version when deployed")
    enabled: bool = Field(
        True,
        description="Whether users may provision it (a template with no settings "
                    "row is enabled). Independent of deployed: disabling hides a "
                    "live template, deploying a disabled one keeps it hidden.",
    )
    customized: bool = Field(
        False,
        description="Operator-edited on disk, so no longer re-synced from the repo",
    )
    workspace_count: int = Field(0, description="Workspaces currently on this template")
    running_workspace_count: int = Field(
        0,
        description="Workspaces of this template counting against its seat quota "
                    "— the same rule the quota itself enforces (a start build in "
                    "an active state).",
    )


class TemplateCatalogResponse(BaseModel):
    """Every workspace template the deployment ships, deployed or not."""

    templates: list[TemplateCatalogEntry] = Field(default_factory=list)
    templates_dir_available: bool = Field(
        True,
        description="False when the backend cannot read the templates directory, "
                    "in which case only already-deployed templates are listed.",
    )


# Workspace volumes (home + scratch), managed through the coder worker

class WorkspaceVolume(BaseModel):
    """One coder-home-* / coder-scratch-* docker volume."""

    name: str = Field(..., description="Docker volume name")
    kind: str = Field(..., description="'home' (shared per user) or 'scratch' (per workspace)")
    size_bytes: Optional[int] = Field(
        None, description="Size on disk; null when docker has not computed it"
    )
    in_use: Optional[bool] = Field(
        None, description="A container currently mounts it — deletion will be refused"
    )
    created_at: Optional[str] = Field(None, description="Docker's creation timestamp")
    user_id: Optional[str] = Field(None, description="Computor user this home belongs to")
    user_name: Optional[str] = Field(None, description="Display name / email of that user")
    workspace_name: Optional[str] = Field(
        None, description="For a scratch volume, the workspace it belongs to"
    )
    orphaned: bool = Field(
        False,
        description="Nothing references it any more: the Coder user or workspace the "
                    "name points at no longer exists. Safe to reclaim.",
    )


class WorkspaceVolumeListResponse(BaseModel):
    """All workspace volumes with their sizes and owners."""

    volumes: list[WorkspaceVolume] = Field(default_factory=list)
    total_bytes: int = Field(0, description="Sum of the known sizes")
    unresolved: bool = Field(
        False,
        description="Coder was unreachable, so owners could not be resolved and nothing "
                    "is reported as orphaned (absence of an owner would be misleading)",
    )


# Template settings (DB-backed resource limits, quota, variable overrides)

class WorkspaceTemplateSettingsSchema(BaseModel):
    """Per-template settings row (see model.workspace.WorkspaceTemplateSettings)."""

    template_name: str = Field(..., description="Coder template name (e.g. 'vscode-workspace')")
    enabled: bool = Field(
        True,
        description="Whether non-managers may see and provision this template; "
                    "disabling hides it from listings and blocks new workspaces, "
                    "existing ones keep running",
    )
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
    allow_root: bool = Field(
        False,
        description="Whether workspaces of this template may use sudo/su. The CEILING: "
                    "a course can narrow it further but never grant root the template "
                    "denies. Applied at the next template push.",
    )
    allow_internet: bool = Field(
        True,
        description="Whether workspaces of this template reach the internet. The CEILING, "
                    "same narrowing rule as allow_root. Applied at the next template push.",
    )
    template_variables: dict[str, str] = Field(
        default_factory=dict,
        description="Extra Terraform variable overrides pushed as --variable "
                    "(only to templates that declare them)",
    )
    updated_at: Optional[datetime] = Field(None, description="Last settings change")


class WorkspaceTemplateSettingsUpdate(BaseModel):
    """Upsert payload for a template's settings."""

    enabled: bool = Field(True)
    memory_mb: Optional[int] = Field(None, ge=0)
    cpu_shares: Optional[int] = Field(
        None, ge=0, description="0 = Docker default; Docker requires values >= 2 otherwise"
    )
    max_running_workspaces: Optional[int] = Field(None, ge=0)
    allow_root: bool = Field(
        False, description="Grant sudo/su in this template's workspaces (ceiling)"
    )
    allow_internet: bool = Field(
        True, description="Allow internet egress from this template's workspaces (ceiling)"
    )
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
    """One Terraform variable declared by a template (settings-override pick-list)."""

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
        description="Owned by the deployment (push pipeline, environment, or "
                    "infrastructure wiring) — cannot be overridden by managers",
    )
    managed_reason: Optional[str] = None
    file: str = Field(..., description="The .tf file declaring this variable")


class TemplateVariablesResponse(BaseModel):
    """Declared variables of a deployed template."""

    template_name: str
    dir_name: str
    customized: bool
    variables: list[TemplateVariable] = Field(default_factory=list)


class WorkspaceCredentialOutcome(BaseModel):
    """What happened to one workspace when a rotated credential was pushed."""

    workspace_name: str
    success: bool = False
    error: Optional[str] = Field(
        None, description="Why it failed, or why it was skipped"
    )


class WorkspaceCredentialRotationResponse(BaseModel):
    """Result of rotating a user's workspace app credential."""

    user_id: str
    key_version: int = Field(..., description="Key version now in effect")
    rotated_at: Optional[datetime] = None
    pushed: bool = Field(
        True,
        description="False when no push was attempted — Coder disabled, or the "
                    "user has no Coder account. The version bump still revoked "
                    "the old credential.",
    )
    outcomes: list[WorkspaceCredentialOutcome] = Field(default_factory=list)
    succeeded: int = 0
    failed: int = 0
