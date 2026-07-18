"""
FastAPI router for Coder workspace management.

This router provides endpoints for on-demand workspace provisioning.
"""

import asyncio
import logging
import re
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from computor_backend.coder.client import CoderClient, get_coder_client
from computor_backend.coder.config import CoderSettings, get_coder_settings
from computor_backend.coder.exceptions import (
    CoderAPIError,
    CoderAuthenticationError,
    CoderConflictError,
    CoderConnectionError,
    CoderDisabledError,
    CoderNotFoundError,
    CoderTemplateNotFoundError,
)
from computor_backend.coder.naming import derive_workspace_name, sanitize_workspace_name
from computor_backend.exceptions import (
    BadRequestException,
    ComputorException,
    ConflictException,
    ForbiddenException,
    InternalServerException,
    NotFoundException,
    ServiceUnavailableException,
)
from computor_types.coder import (
    CoderAdminTaskResponse,
    CoderAdminTaskListResponse,
    CoderFleetStatusResponse,
    CoderHealthResponse,
    CoderLoginRequest,
    CoderSessionResponse,
    CoderTemplateFleetStatus,
    ImageBuildRequest,
    ProvisionResult,
    TemplateFile,
    TemplateFileActionResponse,
    TemplateFileUpdateRequest,
    TemplateFilesResponse,
    TemplatePushRequest,
    TemplateListResponse,
    TemplateSettingsListResponse,
    TemplateVariable,
    TemplateVariablesResponse,
    TemplateVariableUpdateRequest,
    WorkspaceActionResponse,
    WorkspaceDetails,
    WorkspaceListResponse,
    WorkspaceRolloutRequest,
    WorkspaceTemplateSettingsSchema,
    WorkspaceTemplateSettingsUpdate,
)
from computor_backend.coder import templates_fs
from computor_backend.model.workspace import WorkspaceTemplateSettings
from computor_backend.tasks import get_task_executor, TaskSubmission
from computor_types.tasks import TaskInfo
from computor_types.workspace_roles import WorkspaceProvisionRequest
from computor_backend.coder.service import (
    get_user_by_email,
    get_user_by_id,
    get_user_email,
    get_user_fullname,
    mint_workspace_token,
)
from computor_backend.database import get_db
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.redis_cache import get_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/coder", tags=["coder", "workspaces"])


def _check_workspace_access(permissions: Principal, action: str = "access") -> None:
    """Check if the principal has a specific workspace permission."""
    if permissions.is_admin:
        return
    if not permissions.permitted("workspace", action):
        raise ForbiddenException(
            detail=f"Workspace '{action}' permission required. Contact your administrator.",
        )


def _handle_coder_error(e: Exception) -> ComputorException:
    """Convert Coder exceptions to typed ComputorException instances.

    Returned (not raised) so callers can ``raise _handle_coder_error(e) from e``
    and preserve the cause chain via ``from e``.
    """
    if isinstance(e, CoderDisabledError):
        return ServiceUnavailableException(detail="Coder integration is disabled")
    if isinstance(e, CoderConnectionError):
        return ServiceUnavailableException(detail="Cannot connect to Coder server")
    if isinstance(e, CoderAuthenticationError):
        return ServiceUnavailableException(
            detail="Coder admin authentication failed — check CODER_ADMIN_EMAIL and CODER_ADMIN_PASSWORD in .env",
        )
    if isinstance(e, CoderNotFoundError):
        return NotFoundException(detail=str(e))
    if isinstance(e, CoderConflictError):
        # e.g. workspace name already taken by a different template
        return ConflictException(detail=e.detail or str(e))
    if isinstance(e, CoderAPIError):
        # CoderAPIError carries its own status_code; surface 4xx as bad request,
        # 5xx as internal — handlers will pick the right log severity.
        if e.status_code and 400 <= e.status_code < 500:
            return BadRequestException(detail=e.message)
        return InternalServerException(detail=e.message)
    logger.exception("Unexpected Coder error")
    return InternalServerException(detail="Internal Coder error")


async def require_coder_enabled(
    settings: Annotated[CoderSettings, Depends(get_coder_settings)],
) -> CoderSettings:
    """Dependency to check if Coder is enabled."""
    if not settings.enabled:
        raise CoderDisabledError()
    return settings


# Builds counted against a template's max_running_workspaces quota: the
# latest build is a start whose job is queued, applying, or applied.
_ACTIVE_BUILD_STATUSES = {"pending", "starting", "running", "succeeded"}


def _template_settings_row(
    db: Session, template_name: str
) -> Optional[WorkspaceTemplateSettings]:
    return (
        db.query(WorkspaceTemplateSettings)
        .filter(WorkspaceTemplateSettings.template_name == template_name)
        .first()
    )


async def _enforce_template_quota(
    db: Session,
    client: CoderClient,
    template_name: str,
    exclude_workspace_id: Optional[str] = None,
) -> None:
    """Reject provision/start when the template is at its running-seat cap.

    The cap counts running/starting workspaces of the template across ALL
    users and applies to everyone, admins included — it models hard capacity
    (e.g. MATLAB license seats), which exceeding would break anyway. A soft
    check (two racing starts can both pass), which is acceptable for a cap
    whose violation just means one container too many until the next stop.
    """
    row = _template_settings_row(db, template_name)
    if row is None or row.max_running_workspaces is None:
        return
    limit = int(row.max_running_workspaces)
    workspaces = await client.list_all_workspaces()
    active = 0
    for workspace in workspaces:
        if workspace.template_name != template_name:
            continue
        if exclude_workspace_id and workspace.id == exclude_workspace_id:
            continue
        if workspace.latest_build_transition != "start":
            continue
        status = (
            workspace.latest_build_status.value if workspace.latest_build_status else ""
        )
        if status in _ACTIVE_BUILD_STATUSES:
            active += 1
    if active >= limit:
        raise ConflictException(
            detail=(
                f"Template '{template_name}' is at its capacity of {limit} running "
                f"workspace(s) ({active} currently active). Stop an existing "
                "workspace or try again later."
            ),
        )


# Terraform variables the push pipeline always supplies as --variable values.
# Their file defaults are dead (a push always overrides them), so the guided
# variable editor locks them and the settings overrides reject them.
_PUSH_MANAGED_VARIABLES = {
    "computor_backend_internal": "set by the deployment at push time",
    "computor_backend_url": "set by the deployment at push time",
    "dev_forward_ports": "set by the deployment at push time",
    "workspace_image": "pinned to the built image at push time",
    "memory_mb": "managed via the template's resource limit settings",
    "cpu_shares": "managed via the template's resource limit settings",
}

_TF_VARIABLE_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_-]*$")


def _managed_variable_reasons(db: Session, template_name: str) -> dict:
    """Variable name → why guided editing is locked for it."""
    reasons = dict(_PUSH_MANAGED_VARIABLES)
    for name in _deployment_template_variables():
        reasons.setdefault(name, "set from the deployment environment at push time")
    row = _template_settings_row(db, template_name)
    for name in (row.template_variables or {}) if row else ():
        reasons.setdefault(name, "overridden in this template's settings")
    return reasons


def _resolve_template_fs(settings: CoderSettings, template_name: str) -> tuple:
    """(dir_name, absolute path) of a deployed template dir, or raise."""
    root = templates_fs.resolve_templates_root(settings.templates_dir)
    if root is None:
        raise ServiceUnavailableException(
            detail="Template files are not accessible from the backend — the "
                   "templates directory is not mounted or configured "
                   "(CODER_TEMPLATES_DIR).",
        )
    resolved = templates_fs.resolve_template_dir(root, template_name)
    if resolved is None:
        raise NotFoundException(
            detail=f"Template '{template_name}' not found in the templates directory.",
        )
    return resolved


# -----------------------------------------------------------------------------
# Health check endpoint (no auth required)
# -----------------------------------------------------------------------------

@router.get(
    "/health",
    response_model=CoderHealthResponse,
    summary="Check Coder server health",
)
async def health_check(
    _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
    client: Annotated[CoderClient, Depends(get_coder_client)],
) -> CoderHealthResponse:
    """Check if Coder server is reachable and healthy."""
    try:
        healthy, version = await client.health_check()
        return CoderHealthResponse(
            healthy=healthy,
            version=version,
            message="Coder server is healthy" if healthy else "Coder server is unhealthy",
        )
    except Exception as e:
        return CoderHealthResponse(
            healthy=False,
            message=str(e),
        )


# -----------------------------------------------------------------------------
# Template endpoints
# -----------------------------------------------------------------------------

@router.get(
    "/templates",
    response_model=TemplateListResponse,
    summary="List available workspace templates",
)
async def list_templates(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
    client: Annotated[CoderClient, Depends(get_coder_client)],
) -> TemplateListResponse:
    """List all available workspace templates. Requires workspace:templates."""
    _check_workspace_access(permissions, "templates")
    try:
        templates = await client.list_templates()
        return TemplateListResponse(
            templates=templates,
            count=len(templates),
        )
    except Exception as e:
        raise _handle_coder_error(e) from e


# -----------------------------------------------------------------------------
# Workspace provisioning
# -----------------------------------------------------------------------------

@router.post(
    "/workspaces/provision",
    response_model=ProvisionResult,
    summary="Provision a workspace",
)
async def provision_workspace(
    request: WorkspaceProvisionRequest,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
    client: Annotated[CoderClient, Depends(get_coder_client)],
    db: Annotated[Session, Depends(get_db)],
    cache: Annotated[object, Depends(get_cache)],
) -> ProvisionResult:
    """
    Provision a workspace.

    If `email` is provided, provisions for that user (requires workspace:provision permission).
    If `email` is omitted, provisions for the current user.

    Full provisioners (admin or workspace:provision) may provision for any user
    with a custom name. Workspace users (workspace:provision_self) may provision
    only for themselves, one workspace per template — the request is forced to
    their own account and the derived per-template name, so Coder's per-user name
    uniqueness caps them at one (re-provisioning idempotently refreshes its token).
    """
    is_full_provisioner = permissions.is_admin or permissions.permitted("workspace", "provision")
    if not is_full_provisioner:
        if not permissions.permitted("workspace", "provision_self"):
            raise ForbiddenException(
                detail="Workspace 'provision' permission required. Contact your administrator.",
            )
        # Self-service: never allow targeting another user, and always use the
        # derived per-template name so the user gets at most one per template.
        if request.email:
            own_user = get_user_by_id(db, cache, str(permissions.user_id))
            own_email = (get_user_email(own_user) or "").lower() if own_user else ""
            if request.email.strip().lower() != own_email:
                raise ForbiddenException(
                    detail="You may only provision a workspace for yourself.",
                )
            request.email = None
        request.workspace_name = None
    try:
        # Verify template exists in Coder before minting a token
        template = request.template or settings.default_template
        try:
            await client.get_template_id(template)
        except CoderTemplateNotFoundError as e:
            raise ServiceUnavailableException(
                detail=f"Template '{template}' is not yet available. Coder may still be initializing.",
            ) from e

        # Resolve the effective workspace name BEFORE minting, so the
        # per-workspace token name matches the actual workspace name.
        if request.workspace_name:
            workspace_name = sanitize_workspace_name(request.workspace_name)
            if not workspace_name:
                raise BadRequestException(
                    detail=f"Invalid workspace name '{request.workspace_name}'",
                )
        else:
            workspace_name = derive_workspace_name(template)

        # Resolve target user
        if request.email:
            target_user = get_user_by_email(db, cache, request.email)
            if not target_user:
                raise NotFoundException(
                    detail=f"User with email {request.email} not found",
                )
        else:
            target_user = get_user_by_id(db, cache, str(permissions.user_id))

        # Per-template seat quota (max running workspaces across ALL users).
        # Re-provisioning an already-active workspace must not count itself,
        # so its id is excluded when it exists.
        exclude_workspace_id = None
        try:
            coder_user = await client._find_user_by_email(get_user_email(target_user))
            existing = await client.get_user_workspaces(coder_user.username)
            exclude_workspace_id = next(
                (w.id for w in existing if w.name == workspace_name), None
            )
        except CoderNotFoundError:
            pass
        await _enforce_template_quota(
            db, client, template, exclude_workspace_id=exclude_workspace_id
        )

        # Mint workspace token (bounded lifetime; rotated on each provision of
        # this workspace — tokens of the user's other workspaces stay valid)
        workspace_token = mint_workspace_token(
            db, cache, str(target_user.id), str(permissions.user_id),
            workspace_name=workspace_name,
            ttl_days=settings.workspace_token_ttl_days,
        )
        if workspace_token:
            logger.info(f"Token minted (prefix: {workspace_token[:15]}..., length: {len(workspace_token)})")
        else:
            logger.error("Token minting returned None!")

        result = await client.provision_workspace(
            user_email=get_user_email(target_user),
            username=str(target_user.id),
            full_name=get_user_fullname(target_user),
            template=template,
            workspace_name=workspace_name,
            computor_auth_token=workspace_token,
        )
        return result
    except ComputorException:
        # Typed exceptions (ServiceUnavailableException, NotFoundException, …) already
        # carry the right status — let them propagate untouched. (The old clause named
        # an unimported HTTPException, which raised NameError and masked these.)
        raise
    except Exception as e:
        raise _handle_coder_error(e) from e


# -----------------------------------------------------------------------------
# Workspace listing
# -----------------------------------------------------------------------------

@router.get(
    "/workspaces",
    response_model=WorkspaceListResponse,
    summary="Get workspaces",
)
async def get_workspaces(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
    client: Annotated[CoderClient, Depends(get_coder_client)],
    db: Annotated[Session, Depends(get_db)],
    cache: Annotated[object, Depends(get_cache)],
    email: Optional[str] = None,
) -> WorkspaceListResponse:
    """
    Get workspaces.

    If `email` query param is provided, returns workspaces for that user (requires workspace:manage).
    If omitted, returns workspaces for the current user.
    """
    if email:
        _check_workspace_access(permissions, "manage")
        target_email = email
    else:
        _check_workspace_access(permissions, "list")
        user = get_user_by_id(db, cache, str(permissions.user_id))
        target_email = get_user_email(user)

    try:
        coder_user = await client._find_user_by_email(target_email)
        workspaces = await client.get_user_workspaces(coder_user.username)
        return WorkspaceListResponse(
            workspaces=workspaces,
            count=len(workspaces),
        )
    except CoderNotFoundError:
        return WorkspaceListResponse(workspaces=[], count=0)
    except Exception as e:
        raise _handle_coder_error(e) from e


@router.get(
    "/workspaces/all",
    response_model=WorkspaceListResponse,
    summary="List all workspaces (admin fleet view)",
)
async def list_all_workspaces_endpoint(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
    client: Annotated[CoderClient, Depends(get_coder_client)],
) -> WorkspaceListResponse:
    """List every workspace on the server, across all users. Requires
    workspace:manage — the fleet view behind the admin rollout."""
    _check_workspace_access(permissions, "manage")
    try:
        workspaces = await client.list_all_workspaces()
        return WorkspaceListResponse(workspaces=workspaces, count=len(workspaces))
    except Exception as e:
        raise _handle_coder_error(e) from e


@router.get(
    "/workspaces/exists",
    response_model=bool,
    summary="Check if user has any workspaces",
)
async def workspace_exists(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
    client: Annotated[CoderClient, Depends(get_coder_client)],
    db: Annotated[Session, Depends(get_db)],
    cache: Annotated[object, Depends(get_cache)],
    email: Optional[str] = None,
) -> bool:
    """
    Check if a user has any workspaces.

    If `email` query param is provided, checks for that user (requires workspace:manage).
    If omitted, checks for the current user.
    """
    if email:
        _check_workspace_access(permissions, "manage")
        target_email = email
    else:
        _check_workspace_access(permissions, "list")
        user = get_user_by_id(db, cache, str(permissions.user_id))
        target_email = get_user_email(user)

    try:
        coder_user = await client._find_user_by_email(target_email)
        workspaces = await client.get_user_workspaces(coder_user.username)
        return len(workspaces) > 0
    except CoderNotFoundError:
        return False
    except Exception as e:
        raise _handle_coder_error(e) from e


# -----------------------------------------------------------------------------
# Workspace details and lifecycle endpoints
# -----------------------------------------------------------------------------

@router.get(
    "/workspaces/{username}/{workspace_name}",
    response_model=WorkspaceDetails,
    summary="Get workspace details",
)
async def get_workspace_details(
    username: str,
    workspace_name: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
    client: Annotated[CoderClient, Depends(get_coder_client)],
) -> WorkspaceDetails:
    """Get detailed information about a specific workspace."""
    _check_workspace_access(permissions)
    try:
        return await client.get_workspace(username, workspace_name)
    except Exception as e:
        raise _handle_coder_error(e) from e


@router.post(
    "/workspaces/{username}/{workspace_name}/start",
    response_model=WorkspaceActionResponse,
    summary="Start a workspace",
)
async def start_workspace(
    username: str,
    workspace_name: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
    client: Annotated[CoderClient, Depends(get_coder_client)],
    db: Annotated[Session, Depends(get_db)],
) -> WorkspaceActionResponse:
    """Start a stopped workspace."""
    _check_workspace_access(permissions, "start")
    try:
        # Per-template seat quota — the workspace being started never counts
        # itself (it is stopped, but its latest build may still read "start").
        details = await client.get_workspace(username, workspace_name)
        if details.workspace.template_name:
            await _enforce_template_quota(
                db,
                client,
                details.workspace.template_name,
                exclude_workspace_id=details.workspace.id,
            )
        success = await client.start_workspace(username, workspace_name)
        return WorkspaceActionResponse(
            success=success,
            message="Workspace starting" if success else "Failed to start workspace",
        )
    except ComputorException:
        raise
    except Exception as e:
        raise _handle_coder_error(e) from e


@router.post(
    "/workspaces/{username}/{workspace_name}/stop",
    response_model=WorkspaceActionResponse,
    summary="Stop a workspace",
)
async def stop_workspace(
    username: str,
    workspace_name: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
    client: Annotated[CoderClient, Depends(get_coder_client)],
) -> WorkspaceActionResponse:
    """Stop a running workspace."""
    _check_workspace_access(permissions, "stop")
    try:
        success = await client.stop_workspace(username, workspace_name)
        return WorkspaceActionResponse(
            success=success,
            message="Workspace stopping" if success else "Failed to stop workspace",
        )
    except Exception as e:
        raise _handle_coder_error(e) from e


@router.delete(
    "/workspaces/{username}/{workspace_name}",
    response_model=WorkspaceActionResponse,
    summary="Delete a workspace",
)
async def delete_workspace(
    username: str,
    workspace_name: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
    client: Annotated[CoderClient, Depends(get_coder_client)],
) -> WorkspaceActionResponse:
    """Delete a workspace."""
    _check_workspace_access(permissions, "delete")
    try:
        success = await client.delete_workspace(username, workspace_name)
        return WorkspaceActionResponse(
            success=success,
            message="Workspace deleted" if success else "Failed to delete workspace",
        )
    except Exception as e:
        raise _handle_coder_error(e) from e


# -----------------------------------------------------------------------------
# Coder session endpoint
# -----------------------------------------------------------------------------

@router.post(
    "/session",
    response_model=CoderSessionResponse,
    summary="Get a Coder session token",
)
async def get_coder_session(
    request: CoderLoginRequest,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
    client: Annotated[CoderClient, Depends(get_coder_client)],
    db: Annotated[Session, Depends(get_db)],
    cache: Annotated[object, Depends(get_cache)],
) -> CoderSessionResponse:
    """Login to Coder and get a session token."""
    _check_workspace_access(permissions, "session")
    try:
        user = get_user_by_id(db, cache, str(permissions.user_id))
        session_token = await client.login_user(get_user_email(user), request.password)
        if session_token:
            return CoderSessionResponse(
                success=True,
                session_token=session_token,
                message="Login successful",
            )
        return CoderSessionResponse(
            success=False,
            message="Invalid credentials",
        )
    except Exception as e:
        logger.error(f"Coder login error: {e}")
        return CoderSessionResponse(
            success=False,
            message="Login failed",
        )


# -----------------------------------------------------------------------------
# Admin endpoints — image building + template pushing (workspace:manage)
# -----------------------------------------------------------------------------

CODER_ADMIN_TASKS = {
    "build_workspace_images",
    "push_coder_templates",
    "rollout_workspaces",
}


async def _recent_coder_tasks(limit: int = 20) -> list[TaskInfo]:
    """Return recent Coder administration workflows with queryable progress."""
    executor = get_task_executor()
    listed = await executor.list_tasks(limit=max(limit * 5, 100))
    candidates = [
        row for row in listed.get("tasks", [])
        if row.get("task_name") in CODER_ADMIN_TASKS
    ][:limit]
    tasks: list[TaskInfo] = []
    for row in candidates:
        workflow_id = row.get("workflow_id") or row.get("task_id")
        if not workflow_id:
            continue
        try:
            tasks.append(await executor.get_task_status(workflow_id))
        except Exception:
            logger.warning("Could not load Coder workflow %s", workflow_id, exc_info=True)
    return tasks


async def _reject_conflicting_coder_task() -> None:
    """Keep image GC/template activation/rollout operations from racing."""
    executor = get_task_executor()
    listed = await executor.list_tasks(limit=1000, status="STARTED")
    active = next(
        (
            row
            for row in listed.get("tasks", [])
            if row.get("task_name") in CODER_ADMIN_TASKS
        ),
        None,
    )
    if active:
        workflow_id = active.get("workflow_id") or active.get("task_id")
        raise ConflictException(
            detail=(
                f"Coder update operation '{active.get('task_name')}' is already running "
                f"({workflow_id})"
            )
        )


@router.get(
    "/admin/fleet",
    response_model=CoderFleetStatusResponse,
    summary="Get template-centric workspace fleet status",
)
async def get_workspace_fleet_status(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
    client: Annotated[CoderClient, Depends(get_coder_client)],
) -> CoderFleetStatusResponse:
    """Return rollout readiness and technical health for workspace maintainers."""
    _check_workspace_access(permissions, "manage")
    try:
        (healthy, version), templates, workspaces = await asyncio.gather(
            client.health_check(),
            client.list_templates(),
            client.list_all_workspaces(),
        )
    except Exception as e:
        raise _handle_coder_error(e) from e

    by_template: dict[str, list] = {}
    for workspace in workspaces:
        by_template.setdefault(workspace.template_id, []).append(workspace)

    rows: list[CoderTemplateFleetStatus] = []
    for template in templates:
        template_workspaces = by_template.get(template.id, [])
        current = 0
        outdated = 0
        running_outdated = 0
        scheduled = 0
        actionable = 0
        for workspace in template_workspaces:
            is_current = bool(
                template.active_version_id
                and workspace.template_version_id == template.active_version_id
            )
            if is_current:
                current += 1
                continue
            outdated += 1
            status = (
                workspace.latest_build_status.value
                if workspace.latest_build_status
                else ""
            )
            is_running = (
                workspace.latest_build_transition == "start"
                and status in ("succeeded", "running")
            )
            if is_running:
                running_outdated += 1
                actionable += 1
            elif workspace.automatic_updates == "always":
                scheduled += 1
            else:
                actionable += 1

        if not template.active_version_id:
            rollout_state = "unavailable"
        elif actionable:
            rollout_state = "ready"
        elif outdated and scheduled == outdated:
            rollout_state = "scheduled_on_start"
        else:
            rollout_state = "up_to_date"

        rows.append(CoderTemplateFleetStatus(
            id=template.id,
            name=template.name,
            display_name=template.display_name,
            active_version_id=template.active_version_id,
            workspace_count=len(template_workspaces),
            current_count=current,
            outdated_count=outdated,
            running_outdated_count=running_outdated,
            scheduled_on_start_count=scheduled,
            actionable_count=actionable,
            rollout_state=rollout_state,
        ))

    return CoderFleetStatusResponse(
        healthy=healthy,
        version=version,
        templates=rows,
        workspace_count=len(workspaces),
    )


def _deployment_template_variables() -> dict:
    """Optional deployment-wide Terraform variables, applied at push time only
    to templates that declare them (coder rejects undeclared variables). Kept
    out of git in .env — add future settings here.

    matlab_license_file: MATLAB site license (port@host or in-container
    path); empty falls back to in-browser MathWorks sign-in.
    """
    import os

    return {
        "matlab_license_file": os.environ.get("MATLAB_MLM_LICENSE_FILE", ""),
    }


def _per_template_variables(db: Session) -> dict:
    """Per-template Terraform --variable overrides from the settings rows,
    keyed by Coder template name: the resource caps plus any extra variable
    overrides. Values are strings — that's what the coder CLI takes."""
    overrides: dict = {}
    for row in db.query(WorkspaceTemplateSettings).all():
        variables: dict = {}
        if row.memory_mb:
            variables["memory_mb"] = str(row.memory_mb)
        if row.cpu_shares:
            variables["cpu_shares"] = str(row.cpu_shares)
        for name, value in (row.template_variables or {}).items():
            variables[name] = str(value)
        if variables:
            overrides[row.template_name] = variables
    return overrides


def _build_template_parameters(settings: CoderSettings) -> dict:
    """Build common parameters for coder template workflows from settings and env."""
    import os

    debug_mode = os.environ.get("DEBUG_MODE", "development")
    if debug_mode == "production":
        backend_internal = "http://uvicorn:8000"
        backend_external = os.environ.get("BACKEND_EXTERNAL_URL", "")
        forward_ports = ""
    else:
        backend_internal = "http://host.docker.internal:8000"
        backend_external = os.environ.get("BACKEND_EXTERNAL_URL", "http://host.docker.internal:8000")
        forward_ports = os.environ.get("DEV_FORWARD_PORTS", "")

    return {
        "templates_dir": settings.templates_dir,
        "registry_host": settings.registry_host,
        "coder_url": settings.url,
        "coder_admin_email": settings.admin_email,
        "coder_admin_password": settings.admin_password,
        "backend_internal_url": backend_internal,
        "backend_external_url": backend_external,
        "dev_forward_ports": forward_ports,
        "template_variables": _deployment_template_variables(),
        "ttl_ms": settings.workspace_ttl_ms,
        "activity_bump_ms": settings.workspace_activity_bump_ms,
    }


@router.post(
    "/admin/images/build",
    response_model=CoderAdminTaskResponse,
    summary="Build workspace Docker images",
)
async def build_workspace_images(
    request: ImageBuildRequest,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
) -> CoderAdminTaskResponse:
    """
    Trigger workspace image builds via Temporal workflow.
    Requires workspace:manage permission.
    """
    _check_workspace_access(permissions, "manage")
    await _reject_conflicting_coder_task()

    executor = get_task_executor()
    params = {
        "templates": request.templates,
        "templates_dir": settings.templates_dir,
        "registry_host": settings.registry_host,
        "image_tag": request.image_tag,
    }
    submission = TaskSubmission(
        task_name="build_workspace_images",
        parameters=params,
        queue="coder-tasks",
    )
    workflow_id = await executor.submit_task(submission)

    return CoderAdminTaskResponse(
        workflow_id=workflow_id,
        task_name="build_workspace_images",
        status="submitted",
    )


@router.post(
    "/admin/templates/push",
    response_model=CoderAdminTaskResponse,
    summary="Push Coder templates",
)
async def push_coder_templates(
    request: TemplatePushRequest,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
    db: Annotated[Session, Depends(get_db)],
) -> CoderAdminTaskResponse:
    """
    Push Coder templates (Terraform configs) via Temporal workflow.
    Optionally builds images first. Requires workspace:manage permission.
    """
    _check_workspace_access(permissions, "manage")
    await _reject_conflicting_coder_task()

    executor = get_task_executor()
    params = _build_template_parameters(settings)
    # Per-template resource caps + variable overrides are resolved from the DB
    # here at submit time, so the coder worker itself never needs DB access.
    params["per_template_variables"] = _per_template_variables(db)
    params["templates"] = request.templates
    params["build_images"] = request.build_images
    params["image_tag"] = request.image_tag

    submission = TaskSubmission(
        task_name="push_coder_templates",
        parameters=params,
        queue="coder-tasks",
    )
    workflow_id = await executor.submit_task(submission)

    return CoderAdminTaskResponse(
        workflow_id=workflow_id,
        task_name="push_coder_templates",
        status="submitted",
    )


@router.post(
    "/admin/templates/rollout",
    response_model=CoderAdminTaskResponse,
    summary="Roll existing workspaces onto the active template version",
)
async def rollout_workspaces_endpoint(
    request: WorkspaceRolloutRequest,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
) -> CoderAdminTaskResponse:
    """
    Roll every existing workspace onto its template's active version — running
    ones are rebuilt now, stopped ones adopt it on their next start. Run this
    after a template push to propagate a new workspace image/extension to the
    whole fleet. Requires workspace:manage permission.
    """
    _check_workspace_access(permissions, "manage")
    await _reject_conflicting_coder_task()

    executor = get_task_executor()
    submission = TaskSubmission(
        task_name="rollout_workspaces",
        parameters={
            "templates": request.templates,
            "templates_dir": settings.templates_dir,
        },
        queue="coder-tasks",
    )
    workflow_id = await executor.submit_task(submission)

    return CoderAdminTaskResponse(
        workflow_id=workflow_id,
        task_name="rollout_workspaces",
        status="submitted",
    )


# -----------------------------------------------------------------------------
# Admin endpoints — per-template settings + template file editing
# -----------------------------------------------------------------------------


def _settings_row_to_schema(row: WorkspaceTemplateSettings) -> WorkspaceTemplateSettingsSchema:
    return WorkspaceTemplateSettingsSchema(
        template_name=row.template_name,
        memory_mb=row.memory_mb,
        cpu_shares=row.cpu_shares,
        max_running_workspaces=row.max_running_workspaces,
        template_variables=dict(row.template_variables or {}),
        updated_at=row.updated_at,
    )


@router.get(
    "/admin/templates/settings",
    response_model=TemplateSettingsListResponse,
    summary="List per-template settings (resource limits, quota, variable overrides)",
)
async def list_template_settings(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
    db: Annotated[Session, Depends(get_db)],
) -> TemplateSettingsListResponse:
    """All stored settings rows; templates without a row use the defaults
    (unlimited). Requires workspace:manage permission."""
    _check_workspace_access(permissions, "manage")
    rows = db.query(WorkspaceTemplateSettings).order_by(
        WorkspaceTemplateSettings.template_name
    ).all()
    return TemplateSettingsListResponse(
        settings=[_settings_row_to_schema(row) for row in rows],
    )


@router.put(
    "/admin/templates/{template_name}/settings",
    response_model=WorkspaceTemplateSettingsSchema,
    summary="Update a template's settings",
)
async def update_template_settings(
    template_name: str,
    request: WorkspaceTemplateSettingsUpdate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
    db: Annotated[Session, Depends(get_db)],
) -> WorkspaceTemplateSettingsSchema:
    """Upsert resource limits, the running-workspace quota, and Terraform
    variable overrides for one template. Limits and overrides apply at the
    NEXT template push; the quota applies immediately. Requires
    workspace:manage permission."""
    _check_workspace_access(permissions, "manage")

    for name in request.template_variables:
        if not _TF_VARIABLE_NAME_RE.match(name):
            raise BadRequestException(
                detail=f"'{name}' is not a valid Terraform variable name.",
            )
        if name in _PUSH_MANAGED_VARIABLES or name in _deployment_template_variables():
            raise BadRequestException(
                detail=(
                    f"Variable '{name}' cannot be overridden here — it is "
                    f"{_PUSH_MANAGED_VARIABLES.get(name, 'set from the deployment environment at push time')}."
                ),
            )
    if request.cpu_shares is not None and request.cpu_shares == 1:
        raise BadRequestException(
            detail="cpu_shares must be 0 (Docker default) or at least 2.",
        )

    row = _template_settings_row(db, template_name)
    if row is None:
        row = WorkspaceTemplateSettings(
            template_name=template_name,
            created_by=permissions.user_id,
        )
        db.add(row)
    row.memory_mb = request.memory_mb
    row.cpu_shares = request.cpu_shares
    row.max_running_workspaces = request.max_running_workspaces
    row.template_variables = dict(request.template_variables)
    row.updated_by = permissions.user_id
    db.commit()
    db.refresh(row)
    return _settings_row_to_schema(row)


@router.get(
    "/admin/templates/{template_name}/files",
    response_model=TemplateFilesResponse,
    summary="Read a template's Terraform/manifest files",
)
async def get_template_files(
    template_name: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
) -> TemplateFilesResponse:
    """Contents of the deployed template directory's editable files
    (*.tf, *.tftpl, template.json, Dockerfile). Requires workspace:manage."""
    _check_workspace_access(permissions, "manage")
    dir_name, path = _resolve_template_fs(settings, template_name)
    try:
        files = templates_fs.list_template_files(path)
    except OSError as e:
        raise InternalServerException(detail=f"Could not read template files: {e}") from e
    return TemplateFilesResponse(
        template_name=template_name,
        dir_name=dir_name,
        customized=templates_fs.is_customized(path),
        files=[TemplateFile(**f) for f in files],
    )


@router.put(
    "/admin/templates/{template_name}/files/{file_name}",
    response_model=TemplateFileActionResponse,
    summary="Write one template file (raw editing)",
)
async def update_template_file(
    template_name: str,
    file_name: str,
    request: TemplateFileUpdateRequest,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
) -> TemplateFileActionResponse:
    """Overwrite one existing template file after a syntax check (.tf files
    must parse as HCL, template.json as a manifest). Marks the template as
    operator-customized: startup stops re-syncing it from the repo. The
    change takes effect at the next template push. Requires workspace:manage."""
    _check_workspace_access(permissions, "manage")
    _dir_name, path = _resolve_template_fs(settings, template_name)
    try:
        templates_fs.write_template_file(path, file_name, request.content)
    except templates_fs.TemplateFileError as e:
        raise BadRequestException(detail=str(e)) from e
    except OSError as e:
        raise InternalServerException(detail=f"Could not write '{file_name}': {e}") from e
    return TemplateFileActionResponse(
        success=True,
        message=f"'{file_name}' saved. Push the template to apply the change.",
        customized=True,
    )


@router.post(
    "/admin/templates/{template_name}/restore-managed",
    response_model=TemplateFileActionResponse,
    summary="Give a customized template back to automatic repo syncing",
)
async def restore_template_managed(
    template_name: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
) -> TemplateFileActionResponse:
    """Re-create the .computor-managed marker: the repo's template files
    replace the customized ones on the NEXT system startup (customizations
    are lost then). Requires workspace:manage."""
    _check_workspace_access(permissions, "manage")
    _dir_name, path = _resolve_template_fs(settings, template_name)
    try:
        templates_fs.restore_managed(path)
    except OSError as e:
        raise InternalServerException(detail=f"Could not restore marker: {e}") from e
    return TemplateFileActionResponse(
        success=True,
        message="Template is managed again — repo defaults will replace the "
                "customized files on the next system startup.",
        customized=False,
    )


@router.get(
    "/admin/templates/{template_name}/variables",
    response_model=TemplateVariablesResponse,
    summary="List a template's declared Terraform variables (guided editing)",
)
async def get_template_variables(
    template_name: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
    db: Annotated[Session, Depends(get_db)],
) -> TemplateVariablesResponse:
    """Variables parsed from the template's .tf files. Variables the push
    pipeline supplies (or the settings UI owns) are flagged managed — their
    file defaults are dead. Requires workspace:manage."""
    _check_workspace_access(permissions, "manage")
    dir_name, path = _resolve_template_fs(settings, template_name)
    reasons = _managed_variable_reasons(db, template_name)
    variables = []
    for parsed in templates_fs.parse_template_variables(path):
        reason = reasons.get(parsed["name"])
        variables.append(TemplateVariable(
            **parsed,
            managed=reason is not None,
            managed_reason=reason,
        ))
    return TemplateVariablesResponse(
        template_name=template_name,
        dir_name=dir_name,
        customized=templates_fs.is_customized(path),
        variables=variables,
    )


@router.put(
    "/admin/templates/{template_name}/variables",
    response_model=TemplateVariablesResponse,
    summary="Update variable defaults (guided editing)",
)
async def update_template_variables(
    template_name: str,
    request: TemplateVariableUpdateRequest,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
    db: Annotated[Session, Depends(get_db)],
) -> TemplateVariablesResponse:
    """Rewrite the ``default`` of declared, non-managed, non-sensitive
    variables in the template's .tf files (each touched file must re-parse
    before anything is written). Marks the template as operator-customized.
    Takes effect at the next template push. Requires workspace:manage."""
    _check_workspace_access(permissions, "manage")
    dir_name, path = _resolve_template_fs(settings, template_name)
    if not request.defaults:
        raise BadRequestException(detail="No variable defaults provided.")

    reasons = _managed_variable_reasons(db, template_name)
    declared = {v["name"]: v for v in templates_fs.parse_template_variables(path)}
    for name in request.defaults:
        info = declared.get(name)
        if info is None:
            raise BadRequestException(
                detail=f"Variable '{name}' is not declared in this template.",
            )
        if name in reasons:
            raise BadRequestException(
                detail=f"Variable '{name}' is locked — {reasons[name]}.",
            )
        if info["sensitive"]:
            raise BadRequestException(
                detail=f"Variable '{name}' is sensitive — edit it in the raw "
                       "file editor.",
            )

    try:
        templates_fs.update_variable_defaults(path, request.defaults)
    except templates_fs.TemplateFileError as e:
        raise BadRequestException(detail=str(e)) from e
    except OSError as e:
        raise InternalServerException(detail=f"Could not write template files: {e}") from e

    variables = []
    for parsed in templates_fs.parse_template_variables(path):
        reason = reasons.get(parsed["name"])
        variables.append(TemplateVariable(
            **parsed,
            managed=reason is not None,
            managed_reason=reason,
        ))
    return TemplateVariablesResponse(
        template_name=template_name,
        dir_name=dir_name,
        customized=templates_fs.is_customized(path),
        variables=variables,
    )


@router.get(
    "/admin/tasks",
    response_model=CoderAdminTaskListResponse,
    summary="List recent Coder administration tasks",
)
async def list_admin_tasks(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
    limit: int = Query(10, ge=1, le=50),
) -> CoderAdminTaskListResponse:
    """List recent image/template workflows, including their progress queries."""
    _check_workspace_access(permissions, "manage")
    return CoderAdminTaskListResponse(tasks=await _recent_coder_tasks(limit))


@router.get(
    "/admin/tasks/{workflow_id}",
    response_model=TaskInfo,
    summary="Get admin task status",
)
async def get_admin_task_status(
    workflow_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
) -> TaskInfo:
    """Get the status of an admin task (image build / template push)."""
    _check_workspace_access(permissions, "manage")

    executor = get_task_executor()
    try:
        return await executor.get_task_status(workflow_id)
    except Exception as e:
        raise NotFoundException(detail=str(e)) from e
