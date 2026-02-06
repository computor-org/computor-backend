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
    CoderConnectionError,
    CoderDisabledError,
    CoderNotFoundError,
)
from computor_backend.coder.schemas import (
    CoderHealthResponse,
    ProvisionResult,
    TemplateListResponse,
    WorkspaceActionResponse,
    WorkspaceDetails,
    WorkspaceListResponse,
    WorkspaceProvisionRequest,
)
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
# Self-service workspace endpoints
# -----------------------------------------------------------------------------

@router.post(
    "/workspaces/provision",
    response_model=ProvisionResult,
    summary="Provision a workspace for current user",
)
async def provision_workspace(
    request: WorkspaceProvisionRequest,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
    client: Annotated[CoderClient, Depends(get_coder_client)],
    db: Annotated[Session, Depends(get_db)],
    cache: Annotated[object, Depends(get_cache)],
) -> ProvisionResult:
    """Provision a workspace for the current user."""
    _check_workspace_access(permissions, "provision")
    try:
        user = get_user_by_id(db, cache, str(permissions.user_id))
        workspace_token = mint_workspace_token(db, cache, str(user.id), str(permissions.user_id))
        if workspace_token:
            logger.info(f"Self-provision: token minted (prefix: {workspace_token[:15]}..., length: {len(workspace_token)})")
        else:
            logger.error("Self-provision: token minting returned None!")

        result = await client.provision_workspace(
            user_email=get_user_email(user),
            username=str(user.id),
            full_name=get_user_fullname(user),
            template=request.template,
            workspace_name=request.workspace_name,
            computor_auth_token=workspace_token,
        )
        return result
    except Exception as e:
        raise _handle_coder_error(e)


@router.get(
    "/workspaces/me",
    response_model=WorkspaceListResponse,
    summary="Get current user's workspaces",
)
async def get_my_workspaces(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
    client: Annotated[CoderClient, Depends(get_coder_client)],
    db: Annotated[Session, Depends(get_db)],
    cache: Annotated[object, Depends(get_cache)],
) -> WorkspaceListResponse:
    """Get all workspaces for the current authenticated user."""
    _check_workspace_access(permissions, "list")
    try:
        user = get_user_by_id(db, cache, str(permissions.user_id))
        coder_user = await client._find_user_by_email(get_user_email(user))
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
    "/workspaces/me/exists",
    response_model=bool,
    summary="Check if current user has any workspaces",
)
async def my_workspace_exists(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
    client: Annotated[CoderClient, Depends(get_coder_client)],
    db: Annotated[Session, Depends(get_db)],
    cache: Annotated[object, Depends(get_cache)],
) -> bool:
    """Check if the current user has any workspaces in Coder."""
    _check_workspace_access(permissions, "list")
    try:
        user = get_user_by_id(db, cache, str(permissions.user_id))
        coder_user = await client._find_user_by_email(get_user_email(user))
        workspaces = await client.get_user_workspaces(coder_user.username)
        return len(workspaces) > 0
    except CoderNotFoundError:
        return False
    except Exception as e:
        raise _handle_coder_error(e)


# -----------------------------------------------------------------------------
# Admin/manage workspace endpoints
# -----------------------------------------------------------------------------

@router.get(
    "/workspaces/by-email/{email}",
    response_model=WorkspaceListResponse,
    summary="Get workspaces for a user by email (manage)",
)
async def get_workspaces_by_email(
    email: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
    client: Annotated[CoderClient, Depends(get_coder_client)],
) -> WorkspaceListResponse:
    """Get all workspaces for a user identified by email. Requires workspace:manage."""
    _check_workspace_access(permissions, "manage")
    try:
        user = await client._find_user_by_email(email)
        workspaces = await client.get_user_workspaces(user.username)
        return WorkspaceListResponse(
            workspaces=workspaces,
            count=len(workspaces),
        )
    except CoderNotFoundError:
        return WorkspaceListResponse(workspaces=[], count=0)
    except Exception as e:
        raise _handle_coder_error(e)


@router.get(
    "/workspaces/by-email/{email}/exists",
    response_model=bool,
    summary="Check if user has any workspaces (manage)",
)
async def user_has_workspace(
    email: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
    client: Annotated[CoderClient, Depends(get_coder_client)],
) -> bool:
    """Check if a user (by email) has any workspaces. Requires workspace:manage."""
    _check_workspace_access(permissions, "manage")
    try:
        user = await client._find_user_by_email(email)
        workspaces = await client.get_user_workspaces(user.username)
        return len(workspaces) > 0
    except CoderNotFoundError:
        return False
    except Exception as e:
        raise _handle_coder_error(e)


@router.post(
    "/workspaces/by-email/{email}/provision",
    response_model=ProvisionResult,
    summary="Provision workspace for user by email (maintainer)",
)
async def provision_workspace_by_email(
    email: str,
    request: WorkspaceProvisionRequest,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
    client: Annotated[CoderClient, Depends(get_coder_client)],
    db: Annotated[Session, Depends(get_db)],
    cache: Annotated[object, Depends(get_cache)],
) -> ProvisionResult:
    """
    Provision a workspace for a user identified by email.

    Requires workspace:provision permission (maintainers and admins).
    Creates Coder user if needed, then provisions workspace.
    Mints an API token for the workspace extension auto-login.
    """
    _check_workspace_access(permissions, "provision")
    try:
        backend_user = get_user_by_email(db, cache, email)
        if not backend_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with email {email} not found in backend",
            )

        # Mint workspace token
        print(f"[CODER API] About to mint token for user {backend_user.id}")
        workspace_token = mint_workspace_token(db, cache, str(backend_user.id), str(permissions.user_id))
        print(f"[CODER API] Token result: {workspace_token[:20] if workspace_token else 'None'}...")
        if workspace_token:
            logger.info(f"Token minted successfully (prefix: {workspace_token[:15]}..., length: {len(workspace_token)})")
        else:
            logger.error("Token minting returned None!")

        # Provision workspace with user's UUID as username
        result = await client.provision_workspace(
            user_email=email,
            username=str(backend_user.id),
            full_name=get_user_fullname(backend_user),
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
