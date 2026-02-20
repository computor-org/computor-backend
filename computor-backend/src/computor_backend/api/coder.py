"""
FastAPI router for Coder workspace management.

This router provides endpoints for on-demand workspace provisioning.
"""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from computor_backend.coder.client import CoderClient, get_coder_client
from computor_backend.coder.config import CoderSettings, get_coder_settings
from computor_backend.coder.exceptions import (
    CoderAPIError,
    CoderAuthenticationError,
    CoderConnectionError,
    CoderDisabledError,
    CoderNotFoundError,
    CoderTemplateNotFoundError,
)
from computor_backend.coder.schemas import (
    CoderAdminTaskResponse,
    CoderHealthResponse,
    ImageBuildRequest,
    ProvisionResult,
    TemplatePushRequest,
    TemplateListResponse,
    WorkspaceActionResponse,
    WorkspaceDetails,
    WorkspaceListResponse,
)
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
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Workspace '{action}' permission required. Contact your administrator.",
        )


def _handle_coder_error(e: Exception) -> HTTPException:
    """Convert Coder exceptions to HTTP exceptions."""
    if isinstance(e, CoderDisabledError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Coder integration is disabled",
        )
    if isinstance(e, CoderConnectionError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cannot connect to Coder server",
        )
    if isinstance(e, CoderAuthenticationError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Coder is not ready yet (admin setup may still be in progress)",
        )
    if isinstance(e, CoderNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    if isinstance(e, CoderAPIError):
        return HTTPException(
            status_code=e.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message,
        )
    logger.exception(f"Unexpected Coder error: {e}")
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Internal Coder error",
    )


async def require_coder_enabled(
    settings: Annotated[CoderSettings, Depends(get_coder_settings)],
) -> CoderSettings:
    """Dependency to check if Coder is enabled."""
    if not settings.enabled:
        raise CoderDisabledError()
    return settings


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
    _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
    client: Annotated[CoderClient, Depends(get_coder_client)],
) -> TemplateListResponse:
    """List all available workspace templates."""
    try:
        templates = await client.list_templates()
        return TemplateListResponse(
            templates=templates,
            count=len(templates),
        )
    except Exception as e:
        raise _handle_coder_error(e)


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
    _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
    client: Annotated[CoderClient, Depends(get_coder_client)],
    db: Annotated[Session, Depends(get_db)],
    cache: Annotated[object, Depends(get_cache)],
) -> ProvisionResult:
    """
    Provision a workspace.

    If `email` is provided, provisions for that user (requires workspace:provision permission).
    If `email` is omitted, provisions for the current user.
    """
    _check_workspace_access(permissions, "provision")
    try:
        # Verify template exists in Coder before minting a token
        try:
            await client.get_template_id(request.template.value)
        except CoderTemplateNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Template '{request.template.value}' is not yet available. Coder may still be initializing.",
            )

        # Resolve target user
        if request.email:
            target_user = get_user_by_email(db, cache, request.email)
            if not target_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User with email {request.email} not found",
                )
        else:
            target_user = get_user_by_id(db, cache, str(permissions.user_id))

        # Mint workspace token
        workspace_token = mint_workspace_token(db, cache, str(target_user.id), str(permissions.user_id))
        if workspace_token:
            logger.info(f"Token minted (prefix: {workspace_token[:15]}..., length: {len(workspace_token)})")
        else:
            logger.error("Token minting returned None!")

        result = await client.provision_workspace(
            user_email=get_user_email(target_user),
            username=str(target_user.id),
            full_name=get_user_fullname(target_user),
            template=request.template,
            workspace_name=request.workspace_name,
            computor_auth_token=workspace_token,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise _handle_coder_error(e)


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
        raise _handle_coder_error(e)


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
        raise _handle_coder_error(e)


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
        raise _handle_coder_error(e)


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
) -> WorkspaceActionResponse:
    """Start a stopped workspace."""
    _check_workspace_access(permissions, "start")
    try:
        success = await client.start_workspace(username, workspace_name)
        return WorkspaceActionResponse(
            success=success,
            message="Workspace starting" if success else "Failed to start workspace",
        )
    except Exception as e:
        raise _handle_coder_error(e)


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
        raise _handle_coder_error(e)


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
        raise _handle_coder_error(e)


# -----------------------------------------------------------------------------
# Coder session endpoint
# -----------------------------------------------------------------------------

class CoderLoginRequest(BaseModel):
    """Request to login to Coder."""
    password: str
    redirect_url: Optional[str] = None


class CoderSessionResponse(BaseModel):
    """Response with Coder session token."""
    success: bool
    session_token: Optional[str] = None
    message: str


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


def _build_template_parameters(settings: CoderSettings) -> dict:
    """Build common parameters for coder template workflows from settings and env."""
    import os

    debug_mode = os.environ.get("DEBUG_MODE", "development")
    if debug_mode == "production":
        backend_internal = "http://uvicorn:8000"
        backend_external = os.environ.get("BACKEND_EXTERNAL_URL_PROD", "")
        forward_ports = ""
    else:
        backend_internal = "http://host.docker.internal:8000"
        backend_external = os.environ.get("BACKEND_EXTERNAL_URL_DEV", "http://host.docker.internal:8000")
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
        "ttl_ms": 3600000,
        "activity_bump_ms": 3600000,
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

    executor = get_task_executor()
    params = {
        "templates": request.templates,
        "templates_dir": settings.templates_dir,
        "registry_host": settings.registry_host,
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
) -> CoderAdminTaskResponse:
    """
    Push Coder templates (Terraform configs) via Temporal workflow.
    Optionally builds images first. Requires workspace:manage permission.
    """
    _check_workspace_access(permissions, "manage")

    executor = get_task_executor()
    params = _build_template_parameters(settings)
    params["templates"] = request.templates
    params["build_images"] = request.build_images

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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
