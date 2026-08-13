"""
FastAPI router for Coder workspace management.

This router provides endpoints for on-demand workspace provisioning.
"""

import asyncio
import json
import logging
import os
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
from computor_backend.coder.naming import (
    coder_username_matches_user,
    decode_coder_username,
    derive_workspace_name,
    sanitize_workspace_name,
)
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
    TemplateCatalogEntry,
    TemplateCatalogResponse,
    TemplateFile,
    TemplateFileActionResponse,
    TemplateFileUpdateRequest,
    TemplateFilesResponse,
    TemplatePreparation,
    TemplatePushRequest,
    TemplateListResponse,
    TemplateSettingsListResponse,
    TemplateVariable,
    TemplateVariablesResponse,
    WorkspaceActionResponse,
    WorkspaceDetails,
    WorkspaceListResponse,
    WorkspaceRolloutRequest,
    WorkspaceVolume,
    WorkspaceCredentialRotationResponse,
    WorkspaceVolumeListResponse,
    WorkspaceTemplateSettingsSchema,
    WorkspaceTemplateSettingsUpdate,
)
from computor_backend.coder import templates_fs
from computor_backend.model.workspace import WorkspaceTemplateSettings
from computor_backend.tasks import get_task_executor, TaskSubmission
from computor_types.tasks import TaskInfo, TaskStatus
from computor_types.workspace_roles import WorkspaceProvisionRequest
from computor_backend.coder.service import (
    current_workspace_app_credentials,
    get_user_by_email,
    get_user_by_id,
    get_user_email,
    get_user_fullname,
    mint_workspace_token,
)
from computor_backend.business_logic.workspace_credentials import (
    rotate_workspace_app_credential,
)
from computor_backend.business_logic.course_workspaces import (
    ACTIVE_BUILD_STATUSES,
    enforce_template_quota as _enforce_template_quota,
    get_disabled_template_names,
    get_member_course_template_names,
    is_template_enabled,
    list_admin_course_workspaces,
    member_template_policy,
    settings_row_policy,
    template_settings_row as _template_settings_row,
    apply_course_workspace_policy,
    workspace_start_policy,
)
from computor_types.course_workspaces import CourseWorkspaceAdminListResponse
from computor_backend.database import get_db
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.redis_cache import get_cache, get_redis_client

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


# Actions a course member gets without a global workspace role, through being
# in a course with >= 1 allowed (and globally enabled) workspace template.
# manage/delete/session/provision deliberately never fall back.
_COURSE_FALLBACK_ACTIONS = {"access", "list", "start", "stop", "templates"}


def _check_workspace_access_or_course_member(
    permissions: Principal,
    action: str,
    db: Session,
    *,
    username: Optional[str] = None,
) -> None:
    """Global workspace claim, or course-derived access.

    Course-derived callers may only touch their OWN workspaces, so ``username``
    must resolve to the principal. It arrives in Coder form (the web sends the
    workspace's ``owner_name``), which is why this goes through
    ``coder_username_matches_user`` rather than comparing to the bare user id —
    the two are different strings, so an equality check here rejected every
    course-derived caller. Global claim holders keep today's behavior.
    """
    if permissions.is_admin or permissions.permitted("workspace", action):
        return
    if action in _COURSE_FALLBACK_ACTIONS and get_member_course_template_names(db, permissions):
        if username is not None and not coder_username_matches_user(
            username, str(permissions.user_id)
        ):
            raise ForbiddenException(detail="You may only access your own workspaces.")
        return
    raise ForbiddenException(
        detail=f"Workspace '{action}' permission required. Contact your administrator.",
    )


def _current_app_credential_params(db: Session, username: str) -> Optional[dict]:
    """Rich-parameter overrides carrying the owner's current app credential.

    None when the owner has no Computor user behind the Coder name (Coder's own
    ``admin`` account, a deleted user) or when the credential cannot be derived
    — the build then carries the previous values forward, which is the old
    behaviour rather than a workspace nobody can reach.
    """
    owner = _computor_user_for_coder_name(db, username)
    if owner is None:
        return None
    try:
        secret, app_hash = current_workspace_app_credentials(db, str(owner.id))
    except Exception as e:
        logger.warning(f"Could not derive the app credential for '{username}': {e}")
        return None
    return {"workspace_app_secret": secret, "workspace_app_hash": app_hash}


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


# Template quota + settings-row helpers live in business_logic.course_workspaces
# (shared with the course-scoped workspace endpoints); imported above as
# _enforce_template_quota / _template_settings_row.


# Terraform variables the push pipeline always supplies as --variable values.
# Their file defaults are dead (a push always overrides them), so the settings
# overrides reject them and they never appear as manager-editable.
_PUSH_MANAGED_VARIABLES = {
    "computor_backend_internal": "set by the deployment at push time",
    "computor_backend_url": "set by the deployment at push time",
    "dev_forward_ports": "set by the deployment at push time",
    "workspace_image": "pinned to the built image at push time",
    "memory_mb": "managed via the template's resource limit settings",
    "cpu_shares": "managed via the template's resource limit settings",
    "allow_root": "managed via the template's root/internet policy settings",
    "allow_internet": "managed via the template's root/internet policy settings",
}

# Infrastructure wiring: these must match the compose stack (networks, proxy
# paths, internal hosts), so managers cannot override them. The raw file
# editor remains the operator escape hatch.
_INFRA_VARIABLES = {
    "coder_internal_url": "deployment wiring (internal Coder URL)",
    "coder_base_path": "deployment wiring (reverse-proxy base path)",
    "docker_network": "deployment wiring (workspace Docker network)",
    "docker_network_offline": "deployment wiring (no-egress workspace Docker network)",
    "docker_socket": "deployment wiring (Docker socket URI)",
}

_TF_VARIABLE_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_-]*$")

def _computor_user_for_coder_name(db: Session, username: str):
    """The Computor user behind a Coder username, or None.

    Coder usernames decode back to the exact user id (``coder/naming.py``), so
    this is a primary-key lookup. Coder's own `admin` account does not decode
    and simply misses, as does any owner we did not create.
    """
    user_id = decode_coder_username(username)
    if user_id is None:
        return None
    try:
        from computor_backend.model.auth import User

        return db.query(User).filter(User.id == user_id).first()
    except Exception:
        logger.warning(f"Could not resolve Coder username '{username}' to a user")
        return None


def _locked_variable_reasons() -> dict:
    """Variable name → why managers cannot override it in the settings."""
    reasons = {**_PUSH_MANAGED_VARIABLES, **_INFRA_VARIABLES}
    for name in _deployment_template_variables():
        reasons.setdefault(name, "set from the deployment environment at push time")
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
    settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
    client: Annotated[CoderClient, Depends(get_coder_client)],
    db: Annotated[Session, Depends(get_db)],
) -> TemplateListResponse:
    """List available workspace templates.

    Managers (workspace:manage) see everything; workspace:templates holders
    see globally enabled templates; course members without a workspace role
    see the enabled templates their courses allow.

    `preparing` carries the ones an administrator is deploying right now,
    which Coder does not have yet and which therefore cannot be in `templates`
    at all. Without it a user who has been told to use MATLAB opens the page
    mid-build and finds a choice that simply does not include it — and no way
    to tell "not for you" from "twenty minutes away". Scoped identically, so
    it never advertises a template the user could not pick once it lands.
    """
    is_manager = permissions.is_admin or permissions.permitted("workspace", "manage")
    has_templates_claim = permissions.permitted("workspace", "templates")
    course_names: set[str] = set()
    if not (is_manager or has_templates_claim):
        course_names = get_member_course_template_names(db, permissions)
        if not course_names:
            raise ForbiddenException(
                detail="Workspace 'templates' permission required. Contact your administrator.",
            )
    try:
        templates = await client.list_templates()
        live_names = {t.name for t in templates}
        if not is_manager:
            disabled = get_disabled_template_names(db, among=live_names)
            templates = [t for t in templates if t.name not in disabled]
            if course_names:
                templates = [t for t in templates if t.name in course_names]

        preparing = await _template_preparations(
            templates_fs.resolve_templates_root(settings.templates_dir), live_names
        )
        if not is_manager:
            disabled = get_disabled_template_names(db, among={p.name for p in preparing})
            preparing = [p for p in preparing if p.name not in disabled]
            if course_names:
                preparing = [p for p in preparing if p.name in course_names]

        return TemplateListResponse(
            templates=templates,
            count=len(templates),
            preparing=preparing,
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
    Course members without any workspace role get the same self-service
    semantics, restricted to the templates their courses allow.
    """
    is_full_provisioner = permissions.is_admin or permissions.permitted("workspace", "provision")
    course_scoped_names: Optional[set[str]] = None
    if not is_full_provisioner:
        if not permissions.permitted("workspace", "provision_self"):
            course_scoped_names = get_member_course_template_names(db, permissions)
            if not course_scoped_names:
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
        # Self-provisioned workspaces always use the template's default
        # (shared) home; scratch homes are a lecturer/maintainer feature.
        request.home_mode = None
    try:
        # Verify template exists in Coder before minting a token
        template = request.template or settings.default_template
        if course_scoped_names is not None and template not in course_scoped_names:
            raise ForbiddenException(
                detail=f"Template '{template}' is not available for your courses.",
            )
        if not (permissions.is_admin or permissions.permitted("workspace", "manage")):
            # course_scoped_names is already enabled-filtered; this covers
            # global provision/provision_self holders.
            if not is_template_enabled(db, template):
                raise ForbiddenException(
                    detail=f"Template '{template}' is currently disabled.",
                )
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

        # Course-level policy narrowing. Only applies when the caller is
        # provisioning for THEMSELVES, where the courses in their claims are
        # the relevant context — a manager provisioning for someone else is an
        # explicit act, and gets the template's own policy. Either way the
        # template ceiling still applies, so this can only restrict further.
        if request.email:
            policy_root, policy_internet = None, None
        else:
            policy_root, policy_internet = member_template_policy(
                db, permissions, template
            )

        app_secret, app_hash = current_workspace_app_credentials(db, str(target_user.id))
        result = await client.provision_workspace(
            user_email=get_user_email(target_user),
            username=str(target_user.id),
            full_name=get_user_fullname(target_user),
            template=template,
            workspace_name=workspace_name,
            computor_auth_token=workspace_token,
            home_mode=request.home_mode,
            allow_root=policy_root,
            allow_internet=policy_internet,
            app_secret=app_secret,
            app_password_hash=app_hash,
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
        _check_workspace_access_or_course_member(permissions, "list", db)
        user = get_user_by_id(db, cache, str(permissions.user_id))
        target_email = get_user_email(user)

    try:
        coder_user = await client._find_user_by_email(target_email)
        workspaces = await client.get_user_workspaces(coder_user.username)
        # A scratch home is destroyed together with its workspace, a shared one
        # is not. The UI cannot warn about that without knowing which is which,
        # so fill it in here (bounded fan-out, one request per workspace).
        from computor_backend.business_logic.course_workspaces import populate_home_modes
        await populate_home_modes(client, workspaces)
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
        _check_workspace_access_or_course_member(permissions, "list", db)
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
    db: Annotated[Session, Depends(get_db)],
) -> WorkspaceDetails:
    """Get detailed information about a specific workspace."""
    _check_workspace_access_or_course_member(permissions, "access", db, username=username)
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
    _check_workspace_access_or_course_member(permissions, "start", db, username=username)
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
        # A course workspace starts under the course's CURRENT policy, not the
        # one it was created with — otherwise a workspace that happened to be
        # stopped when a lecturer locked the course down comes back unlocked.
        policy = await workspace_start_policy(
            db, client, details.workspace.template_name or "",
            details.workspace.latest_build_id,
        )
        # Every start carries the owner's CURRENT app credential, for course and
        # personal workspaces alike. A workspace that was stopped when the
        # credential was rotated would otherwise come back holding the revoked
        # one — the build parameters are what the container and the ingress are
        # rendered from, and Coder carries them forward untouched.
        overrides = _current_app_credential_params(db, username)
        success = await client.start_workspace(
            username, workspace_name, policy=policy, param_overrides=overrides
        )
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
    db: Annotated[Session, Depends(get_db)],
) -> WorkspaceActionResponse:
    """Stop a running workspace."""
    _check_workspace_access_or_course_member(permissions, "stop", db, username=username)
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


# Deployment runs a user can be waiting on. A rollout is deliberately not one:
# it updates workspaces that already exist and never changes what a user can
# create, and the restart it causes is already reported by the workspace's own
# row — repeating it against a template would be noise.
USER_VISIBLE_CODER_TASKS = (
    "build_workspace_images",
    "push_coder_templates",
)

_FINISHED_TASK_STATUSES = {
    TaskStatus.FINISHED,
    TaskStatus.FAILED,
    TaskStatus.CANCELLED,
}

# The template listing is polled by every workspaces page that is open, and the
# answer behind it is a Temporal query. A build stage lasts minutes, so a few
# seconds of staleness costs a user nothing and keeps a lecture hall's worth of
# pollers off the workflow service.
_PREPARING_CACHE_KEY = "coder:templates:preparing"
_PREPARING_CACHE_TTL = 5


async def _compute_template_preparations(
    templates_root: Optional[str],
) -> list[dict]:
    """Per-template state of the most recent deploy run, as plain dicts.

    Plain dicts rather than models because this is what gets cached: the
    per-user scoping happens afterwards, on the way out.
    """
    try:
        tasks = await _recent_coder_tasks(limit=5)
    except Exception:
        # Never fail a template listing over the progress decoration on it.
        logger.warning("Could not read Coder deployment activity", exc_info=True)
        return []

    task = next((t for t in tasks if t.task_name in USER_VISIBLE_CODER_TASKS), None)
    if task is None:
        return []

    entries = (task.progress or {}).get("templates") or []
    finished = task.status in _FINISHED_TASK_STATUSES
    manifests = templates_fs.discover_templates(templates_root) if templates_root else {}

    preparing: list[dict] = []
    for entry in entries:
        name = entry.get("name") or entry.get("key")
        if not name:
            continue
        status = entry.get("status") or "pending"
        # Succeeded means Coder has it now, so it is in `templates` proper —
        # listing it here too would park a finished bar beside a usable card.
        if status == "succeeded":
            continue
        # A run that is over leaves everything it never reached sitting at
        # 'pending' for good. Of a finished run, only the failures are still
        # true, and they are worth saying: the alternative is a card that read
        # "Building image" quietly vanishing mid-wait.
        if finished and status != "failed":
            continue
        # The workflow's progress carries a display name but no description or
        # icon; the manifest on disk (keyed by directory, as progress is) has
        # both, and is what the template will be pushed with.
        manifest = manifests.get(entry.get("key") or "", {})
        preparing.append({
            "name": name,
            "display_name": entry.get("display_name") or manifest.get("display_name"),
            "description": manifest.get("description"),
            "icon": manifest.get("icon"),
            "status": status,
            "phase": entry.get("phase") or "queued",
            "task_name": task.task_name,
        })
    return preparing


async def _template_preparations(
    templates_root: Optional[str],
    live_names: set[str],
) -> list[TemplatePreparation]:
    """What is being deployed right now, cached for a few seconds."""
    payload: Optional[list[dict]] = None
    try:
        redis = await get_redis_client()
        cached = await redis.get(_PREPARING_CACHE_KEY)
        if cached:
            payload = json.loads(cached)
    except Exception:
        logger.debug("Coder deployment activity cache unavailable", exc_info=True)

    if payload is None:
        payload = await _compute_template_preparations(templates_root)
        try:
            redis = await get_redis_client()
            await redis.set(
                _PREPARING_CACHE_KEY, json.dumps(payload), ex=_PREPARING_CACHE_TTL
            )
        except Exception:
            logger.debug("Could not cache Coder deployment activity", exc_info=True)

    return [
        TemplatePreparation(**item, deployed=item["name"] in live_names)
        for item in payload
    ]


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
            else:
                # Every start through the backend builds on the active version
                # (see CoderClient._workspace_transition), so a stopped
                # outdated workspace is already scheduled to update — the
                # automatic_updates flag no longer gates that.
                scheduled += 1

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
        # Always sent, unlike the caps above: these are booleans whose "off"
        # value is meaningful, and the push filter drops falsy values, so
        # "false" has to travel as the non-empty string it already is.
        allow_root, allow_internet = settings_row_policy(row)
        variables["allow_root"] = "true" if allow_root else "false"
        variables["allow_internet"] = "true" if allow_internet else "false"
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
        forward_ports = ""
    else:
        backend_internal = "http://host.docker.internal:8000"
        forward_ports = os.environ.get("DEV_FORWARD_PORTS", "")

    # What the extension INSIDE a workspace calls. Not the public URL: a
    # workspace reaches the API through workspace-ingress, which answers to this
    # name on the workspace networks and forwards to the backend. Same value in
    # dev and prod — the ingress absorbs the difference (in dev it forwards to
    # the host, where the backend runs) — and it is plain HTTP on an internal
    # name, so no certificate has to exist for a workspace to talk to us.
    backend_external = os.environ.get(
        "WORKSPACE_BACKEND_URL", "http://computor-api"
    )

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
    params["no_cache"] = request.no_cache

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
    ones are rebuilt NOW, stopped ones adopt it on their next start. A push
    already chains in the gentle variant (flags only), so this endpoint exists
    to force-update workspaces that are currently running without waiting for
    their owners to restart them. Requires workspace:manage permission.
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
    allow_root, allow_internet = settings_row_policy(row)
    return WorkspaceTemplateSettingsSchema(
        template_name=row.template_name,
        enabled=bool(row.enabled),
        memory_mb=row.memory_mb,
        cpu_shares=row.cpu_shares,
        max_running_workspaces=row.max_running_workspaces,
        allow_root=allow_root,
        allow_internet=allow_internet,
        template_variables=dict(row.template_variables or {}),
        updated_at=row.updated_at,
    )


@router.get(
    "/admin/courses",
    response_model=CourseWorkspaceAdminListResponse,
    summary="List all courses with their workspace configuration",
)
async def list_admin_courses(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> CourseWorkspaceAdminListResponse:
    """Every course with its allowed templates and lecturer-provisioning flag.

    Claim-gated (workspace:manage), not membership-gated: workspace
    maintainers configure courses they are not members of. Pure DB read, so
    it works while Coder itself is disabled."""
    return list_admin_course_workspaces(permissions, db)


@router.get(
    "/admin/templates/catalog",
    response_model=TemplateCatalogResponse,
    summary="List every workspace template the deployment ships, deployed or not",
)
async def list_template_catalog(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
    client: Annotated[CoderClient, Depends(get_coder_client)],
    db: Annotated[Session, Depends(get_db)],
) -> TemplateCatalogResponse:
    """The union of the templates on disk and the templates live in Coder.

    ``GET /coder/templates`` only ever shows what Coder has, which makes a
    template nobody pushed invisible — and nothing is pushed automatically:
    a fresh deployment starts with none, and an operator picks. This is the
    endpoint that shows them the choice.

    Requires workspace:manage.
    """
    _check_workspace_access(permissions, "manage")
    try:
        coder_templates, workspaces = await asyncio.gather(
            client.list_templates(),
            client.list_all_workspaces(),
        )
    except Exception as e:
        raise _handle_coder_error(e) from e

    workspace_counts: dict[str, int] = {}
    running_counts: dict[str, int] = {}
    for workspace in workspaces:
        workspace_counts[workspace.template_id] = (
            workspace_counts.get(workspace.template_id, 0) + 1
        )
        # The same rule enforce_template_quota() counts by, so the seats column
        # shows the number the quota actually acts on.
        status = (
            workspace.latest_build_status.value
            if workspace.latest_build_status
            else ""
        )
        if workspace.latest_build_transition == "start" and status in ACTIVE_BUILD_STATUSES:
            running_counts[workspace.template_id] = (
                running_counts.get(workspace.template_id, 0) + 1
            )
    live_by_name = {template.name: template for template in coder_templates}

    enabled_by_name = {
        row.template_name: row.enabled
        for row in db.query(WorkspaceTemplateSettings).all()
    }
    root = templates_fs.resolve_templates_root(settings.templates_dir)
    manifests = templates_fs.discover_templates(root) if root else {}

    entries: list[TemplateCatalogEntry] = []
    for dir_name, manifest in manifests.items():
        name = manifest.get("coder_template_name") or dir_name
        live = live_by_name.pop(name, None)
        entries.append(TemplateCatalogEntry(
            dir_name=dir_name,
            name=name,
            display_name=manifest.get("display_name") or (live.display_name if live else None),
            description=manifest.get("description") or (live.description if live else None),
            icon=manifest.get("icon") or (live.icon if live else None),
            image_name=manifest.get("image_name"),
            deployed=live is not None,
            template_id=live.id if live else None,
            active_version_id=live.active_version_id if live else None,
            enabled=enabled_by_name.get(name, True),
            customized=templates_fs.is_customized(os.path.join(root, dir_name)),
            workspace_count=workspace_counts.get(live.id, 0) if live else 0,
            running_workspace_count=running_counts.get(live.id, 0) if live else 0,
        ))

    # Whatever is left is live in Coder without a directory here — still listed,
    # since it is a template users can be on, just not one we can rebuild.
    for name, live in live_by_name.items():
        entries.append(TemplateCatalogEntry(
            dir_name=None,
            name=name,
            display_name=live.display_name,
            description=live.description,
            icon=live.icon,
            deployed=True,
            template_id=live.id,
            active_version_id=live.active_version_id,
            enabled=enabled_by_name.get(name, True),
            workspace_count=workspace_counts.get(live.id, 0),
            running_workspace_count=running_counts.get(live.id, 0),
        ))

    entries.sort(key=lambda entry: (entry.display_name or entry.name).lower())
    return TemplateCatalogResponse(
        templates=entries,
        templates_dir_available=root is not None,
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

    locked = _locked_variable_reasons()
    for name in request.template_variables:
        if not _TF_VARIABLE_NAME_RE.match(name):
            raise BadRequestException(
                detail=f"'{name}' is not a valid Terraform variable name.",
            )
        if name in locked:
            raise BadRequestException(
                detail=(
                    f"Variable '{name}' cannot be overridden here — it is "
                    f"{locked[name]}."
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
    row.enabled = request.enabled
    row.memory_mb = request.memory_mb
    row.cpu_shares = request.cpu_shares
    row.max_running_workspaces = request.max_running_workspaces
    row.allow_root = request.allow_root
    row.allow_internet = request.allow_internet
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
    summary="List a template's declared Terraform variables",
)
async def get_template_variables(
    template_name: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
) -> TemplateVariablesResponse:
    """Variables parsed from the template's .tf files — the pick-list behind
    the settings tab's variable overrides. Variables the deployment owns
    (push pipeline, environment, infrastructure wiring) are flagged managed:
    they cannot be overridden. Requires workspace:manage."""
    _check_workspace_access(permissions, "manage")
    dir_name, path = _resolve_template_fs(settings, template_name)
    reasons = _locked_variable_reasons()
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


async def _run_volume_task(action: str, volume: Optional[str] = None) -> dict:
    """Run one workspace-volume action on the coder worker and wait for it.

    The backend has no docker socket — only the coder worker does — so even
    reading the volume list is a Temporal round trip. Unlike the build/push
    workflows these are short and the caller is a web request, so this awaits
    the result instead of handing back a workflow id to poll.
    """
    executor = get_task_executor()
    submission = TaskSubmission(
        task_name="workspace_volumes",
        parameters={"action": action, "volume": volume},
        queue="coder-tasks",
    )
    workflow_id = await executor.submit_task(submission)
    try:
        result = await asyncio.wait_for(executor.get_task_result(workflow_id), timeout=300)
    except asyncio.TimeoutError:
        raise ServiceUnavailableException(
            detail="The volume operation timed out. Is the coder worker running?",
        )
    payload = result.result if isinstance(result.result, dict) else {}
    # Depending on how Temporal deserialized it, this is either the activity's
    # own dict or the whole WorkflowResult wrapping it. Unwrap one level rather
    # than depend on which.
    if "success" not in payload and isinstance(payload.get("result"), dict):
        payload = payload["result"]
    if not payload.get("success"):
        raise BadRequestException(
            detail=payload.get("error") or result.error or "Volume operation failed",
        )
    return payload


@router.get(
    "/admin/volumes",
    response_model=WorkspaceVolumeListResponse,
    summary="List workspace home and scratch volumes with sizes and owners",
)
async def list_workspace_volumes(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
    client: Annotated[CoderClient, Depends(get_coder_client)],
    db: Annotated[Session, Depends(get_db)],
    cache=Depends(get_cache),
) -> WorkspaceVolumeListResponse:
    """Home volumes (shared per user) and scratch volumes (per workspace).

    These are deliberately not Terraform-managed so a workspace delete can
    never destroy a home — which also means nothing else in the platform can
    see them. Requires workspace:manage.
    """
    _check_workspace_access(permissions, "manage")
    payload = await _run_volume_task("list")

    # Resolve owners. The worker only sees names; matching a `coder-home-{id}`
    # to a person needs Coder (id -> username) and the database (username is
    # the Computor user id). If Coder is unreachable we still return the
    # volumes, but nothing is called orphaned — "no owner found" would then
    # mean "could not look up", which is the opposite of safe to delete.
    users_by_id: dict[str, str] = {}
    workspaces_by_id: dict[str, str] = {}
    unresolved = False
    try:
        users_by_id = {u.id: u.username for u in await client.list_all_users()}
        workspaces_by_id = {w.id: w.name for w in await client.list_all_workspaces()}
    except Exception as e:
        logger.warning(f"Could not resolve volume owners from Coder: {e}")
        unresolved = True

    volumes = []
    total = 0
    for entry in payload.get("volumes", []):
        ref = entry.get("owner_ref") or ""
        user_id = user_name = workspace_name = None
        orphaned = False
        if entry["kind"] == "home":
            username = users_by_id.get(ref)
            if username:
                user = _computor_user_for_coder_name(db, username)
                user_id = str(user.id) if user else username
                if user:
                    user_name = get_user_fullname(user) or get_user_email(user)
            elif not unresolved:
                orphaned = True
        else:
            workspace_name = workspaces_by_id.get(ref)
            if workspace_name is None and not unresolved:
                orphaned = True
        size = entry.get("size_bytes")
        if size:
            total += size
        volumes.append(WorkspaceVolume(
            name=entry["name"],
            kind=entry["kind"],
            size_bytes=size,
            in_use=entry.get("in_use"),
            created_at=entry.get("created_at"),
            user_id=user_id,
            user_name=user_name,
            workspace_name=workspace_name,
            orphaned=orphaned,
        ))
    return WorkspaceVolumeListResponse(
        volumes=volumes, total_bytes=total, unresolved=unresolved
    )


@router.delete(
    "/admin/volumes/{volume_name}",
    response_model=WorkspaceActionResponse,
    summary="Delete a workspace volume",
)
async def delete_workspace_volume(
    volume_name: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
) -> WorkspaceActionResponse:
    """Reclaim a home or scratch volume. Irreversible.

    Deleting a home takes every file of that user with it, across all of their
    workspaces. Refused while a container still mounts it — stop the workspace
    first. Requires workspace:manage.
    """
    _check_workspace_access(permissions, "manage")
    payload = await _run_volume_task("delete", volume_name)
    return WorkspaceActionResponse(success=True, message=payload.get("message", "Deleted"))


@router.post(
    "/admin/volumes/{volume_name}/repair",
    response_model=WorkspaceActionResponse,
    summary="Reset a volume's file ownership to the workspace user",
)
async def repair_workspace_volume(
    volume_name: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
) -> WorkspaceActionResponse:
    """Give the volume's contents back to uid 1000.

    Files a workspace wrote while it had root stay root-owned in the shared
    home; once the template's root access is switched off nothing inside the
    workspace can fix them. Requires workspace:manage.
    """
    _check_workspace_access(permissions, "manage")
    payload = await _run_volume_task("repair", volume_name)
    return WorkspaceActionResponse(success=True, message=payload.get("message", "Repaired"))


@router.post(
    "/admin/users/{user_id}/app-credential/rotate",
    response_model=WorkspaceCredentialRotationResponse,
    summary="Rotate a user's workspace app credential",
)
async def rotate_user_app_credential(
    user_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
    client: Annotated[CoderClient, Depends(get_coder_client)],
    db: Annotated[Session, Depends(get_db)],
    cache=Depends(get_cache),
) -> WorkspaceCredentialRotationResponse:
    """Revoke the credential this user's workspace apps accept, and replace it.

    The secret is derived from a per-user key version, so bumping that version
    is the revocation. Their RUNNING workspaces are then rebuilt under the new
    one — a running container holds the old secret in its environment and in
    the Traefik label that injects it, and nothing short of a rebuild replaces
    either. Stopped workspaces are reported instead of started: every start
    sends the owner's current credential, so they cannot come back accepting
    the revoked one.

    Requires workspace:manage.
    """
    _check_workspace_access(permissions, "manage")
    if get_user_by_id(db, cache, user_id) is None:
        raise NotFoundException(detail=f"User {user_id} not found")
    try:
        return await rotate_workspace_app_credential(db, client, user_id, cache)
    except ComputorException:
        raise
    except Exception as e:
        raise _handle_coder_error(e) from e


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
