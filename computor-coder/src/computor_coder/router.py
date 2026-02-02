"""
FastAPI router for Coder workspace management.

This router provides endpoints for on-demand workspace provisioning.
It's designed to be mounted in the computor-backend following the
standard permissions pattern.
"""

import logging
from typing import Annotated, Any, Callable, Optional, Protocol, runtime_checkable

from fastapi import APIRouter, Depends, HTTPException, status

from .client import CoderClient, get_coder_client
from .config import CoderSettings, get_coder_settings
from .exceptions import (
    CoderAPIError,
    CoderConnectionError,
    CoderDisabledError,
    CoderNotFoundError,
)
from .schemas import (
    CoderHealthResponse,
    ProvisionResult,
    TemplateListResponse,
    WorkspaceActionResponse,
    WorkspaceDetails,
    WorkspaceListResponse,
    WorkspaceProvisionRequest,
)

logger = logging.getLogger(__name__)


@runtime_checkable
class PrincipalProtocol(Protocol):
    """
    Protocol defining the expected interface for Principal objects.

    This matches the computor-backend Principal class interface.
    """

    @property
    def user_id(self) -> Optional[str]:
        """Get user ID."""
        ...

    @property
    def is_admin(self) -> bool:
        """Check if user is admin."""
        ...

    def get_user_id_or_throw(self) -> str:
        """Get user ID or raise exception."""
        ...


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
    # Generic error
    logger.exception(f"Unexpected Coder error: {e}")
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Internal Coder error",
    )


def create_coder_router(
    prefix: str = "/coder",
    tags: Optional[list[str]] = None,
    get_current_principal: Optional[Callable] = None,
    get_user_email: Optional[Callable] = None,
    get_user_fullname: Optional[Callable] = None,
    get_user_id: Optional[Callable] = None,
    dependencies: Optional[list] = None,
) -> APIRouter:
    """
    Create a FastAPI router for Coder workspace management.

    This factory function follows the computor-backend pattern where
    `permissions` (Principal) is injected as a dependency.

    Args:
        prefix: URL prefix for the router
        tags: OpenAPI tags for the endpoints
        get_current_principal: Dependency to get current Principal (permissions)
        get_user_email: Dependency to get user's email (receives permissions)
        get_user_fullname: Optional dependency to get user's full name
        get_user_id: Optional dependency to get user's ID (used as Coder username)
        dependencies: Additional router dependencies

    Returns:
        Configured APIRouter instance

    Example:
        ```python
        from computor_coder import create_coder_router
        from computor_backend.permissions.auth import get_current_principal
        from computor_backend.permissions.principal import Principal
        from computor_backend.database import get_db
        from computor_backend.model.auth import User
        from fastapi import Depends
        from typing import Annotated

        # Define user info dependencies following backend pattern
        async def get_user_email(
            permissions: Annotated[Principal, Depends(get_current_principal)],
            db: Session = Depends(get_db),
        ) -> str:
            user = db.query(User).filter(User.id == permissions.user_id).first()
            return user.email

        async def get_user_fullname(
            permissions: Annotated[Principal, Depends(get_current_principal)],
            db: Session = Depends(get_db),
        ) -> Optional[str]:
            user = db.query(User).filter(User.id == permissions.user_id).first()
            if user.given_name and user.family_name:
                return f"{user.given_name} {user.family_name}"
            return None

        router = create_coder_router(
            get_current_principal=get_current_principal,
            get_user_email=get_user_email,
            get_user_fullname=get_user_fullname,
        )
        app.include_router(router)
        ```
    """
    router = APIRouter(
        prefix=prefix,
        tags=tags or ["coder"],
        dependencies=dependencies or [],
    )

    # Dependency to check if Coder is enabled
    async def require_coder_enabled(
        settings: Annotated[CoderSettings, Depends(get_coder_settings)],
    ) -> CoderSettings:
        if not settings.enabled:
            raise CoderDisabledError()
        return settings

    # Default fullname dependency (returns None if not provided)
    async def _default_fullname() -> Optional[str]:
        return None

    _fullname_dependency = get_user_fullname if get_user_fullname else _default_fullname

    # Default user_id dependency (returns None if not provided)
    async def _default_user_id() -> Optional[str]:
        return None

    _user_id_dependency = get_user_id if get_user_id else _default_user_id

    # -------------------------------------------------------------------------
    # Health check endpoint (no auth required)
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Template endpoints
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Authenticated endpoints (require get_current_principal)
    # -------------------------------------------------------------------------

    if get_current_principal and get_user_email:

        @router.post(
            "/workspaces/provision",
            response_model=ProvisionResult,
            summary="Provision a workspace for current user",
            description="""
            Provision a workspace for the currently authenticated user.

            This endpoint will:
            1. Check if the user exists in Coder (by email)
            2. Create the user in Coder if they don't exist (using provided password)
            3. Check if the user has a workspace
            4. Create a workspace if they don't have one

            **Note**: Password is required in the request body because backend
            passwords are hashed and cannot be retrieved.
            """,
        )
        async def provision_workspace(
            request: WorkspaceProvisionRequest,
            permissions: Annotated[Any, Depends(get_current_principal)],
            _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
            client: Annotated[CoderClient, Depends(get_coder_client)],
            user_email: Annotated[str, Depends(get_user_email)],
            user_fullname: Annotated[Optional[str], Depends(_fullname_dependency)],
            user_id: Annotated[Optional[str], Depends(_user_id_dependency)],
        ) -> ProvisionResult:
            """Provision a workspace for the current user."""
            _ = permissions  # Used by dependencies, logged for audit
            try:
                result = await client.provision_workspace(
                    user_email=user_email,
                    user_password=request.password,
                    username=user_id,  # Use user_id as Coder username if provided
                    full_name=user_fullname,
                    template=request.template,
                    workspace_name=request.workspace_name,
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
            permissions: Annotated[Any, Depends(get_current_principal)],
            _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
            client: Annotated[CoderClient, Depends(get_coder_client)],
            user_email: Annotated[str, Depends(get_user_email)],
        ) -> WorkspaceListResponse:
            """Get all workspaces for the current authenticated user."""
            _ = permissions  # Used by dependencies
            try:
                user = await client._find_user_by_email(user_email)
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
            "/workspaces/me/exists",
            response_model=bool,
            summary="Check if current user has any workspaces",
        )
        async def my_workspace_exists(
            permissions: Annotated[Any, Depends(get_current_principal)],
            _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
            client: Annotated[CoderClient, Depends(get_coder_client)],
            user_email: Annotated[str, Depends(get_user_email)],
        ) -> bool:
            """Check if the current user has any workspaces in Coder."""
            _ = permissions  # Used by dependencies
            try:
                user = await client._find_user_by_email(user_email)
                workspaces = await client.get_user_workspaces(user.username)
                return len(workspaces) > 0
            except CoderNotFoundError:
                return False
            except Exception as e:
                raise _handle_coder_error(e)

    # -------------------------------------------------------------------------
    # Workspace query endpoints (check by email - admin/lookup)
    # -------------------------------------------------------------------------

    @router.get(
        "/workspaces/by-email/{email}",
        response_model=WorkspaceListResponse,
        summary="Get workspaces for a user by email",
    )
    async def get_workspaces_by_email(
        email: str,
        _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
        client: Annotated[CoderClient, Depends(get_coder_client)],
    ) -> WorkspaceListResponse:
        """
        Get all workspaces for a user identified by email.

        This checks the Coder API directly - no database lookup.
        """
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
        summary="Check if user has any workspaces",
    )
    async def user_has_workspace(
        email: str,
        _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
        client: Annotated[CoderClient, Depends(get_coder_client)],
    ) -> bool:
        """Check if a user (by email) has any workspaces in Coder."""
        try:
            user = await client._find_user_by_email(email)
            workspaces = await client.get_user_workspaces(user.username)
            return len(workspaces) > 0
        except CoderNotFoundError:
            return False
        except Exception as e:
            raise _handle_coder_error(e)

    # -------------------------------------------------------------------------
    # Workspace details endpoint
    # -------------------------------------------------------------------------

    @router.get(
        "/workspaces/{username}/{workspace_name}",
        response_model=WorkspaceDetails,
        summary="Get workspace details",
    )
    async def get_workspace_details(
        username: str,
        workspace_name: str,
        _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
        client: Annotated[CoderClient, Depends(get_coder_client)],
    ) -> WorkspaceDetails:
        """Get detailed information about a specific workspace."""
        try:
            return await client.get_workspace(username, workspace_name)
        except Exception as e:
            raise _handle_coder_error(e)

    # -------------------------------------------------------------------------
    # Workspace lifecycle endpoints
    # -------------------------------------------------------------------------

    @router.post(
        "/workspaces/{username}/{workspace_name}/start",
        response_model=WorkspaceActionResponse,
        summary="Start a workspace",
    )
    async def start_workspace(
        username: str,
        workspace_name: str,
        _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
        client: Annotated[CoderClient, Depends(get_coder_client)],
    ) -> WorkspaceActionResponse:
        """Start a stopped workspace."""
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
        _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
        client: Annotated[CoderClient, Depends(get_coder_client)],
    ) -> WorkspaceActionResponse:
        """Stop a running workspace."""
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
        _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
        client: Annotated[CoderClient, Depends(get_coder_client)],
    ) -> WorkspaceActionResponse:
        """Delete a workspace."""
        try:
            success = await client.delete_workspace(username, workspace_name)
            return WorkspaceActionResponse(
                success=success,
                message="Workspace deleted" if success else "Failed to delete workspace",
            )
        except Exception as e:
            raise _handle_coder_error(e)

    # -------------------------------------------------------------------------
    # Coder session/login endpoints
    # -------------------------------------------------------------------------

    if get_current_principal and get_user_email:
        from fastapi.responses import RedirectResponse
        from pydantic import BaseModel

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
            permissions: Annotated[Any, Depends(get_current_principal)],
            _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
            client: Annotated[CoderClient, Depends(get_coder_client)],
            user_email: Annotated[str, Depends(get_user_email)],
        ) -> CoderSessionResponse:
            """
            Login to Coder and get a session token.

            This allows the frontend to authenticate with Coder using the
            user's credentials without storing them.
            """
            _ = permissions
            try:
                session_token = await client.login_user(user_email, request.password)
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

    return router


def create_admin_coder_router(
    prefix: str = "/admin/coder",
    tags: Optional[list[str]] = None,
    get_current_principal: Optional[Callable] = None,
    require_admin: Optional[Callable] = None,
    dependencies: Optional[list] = None,
) -> APIRouter:
    """
    Create an admin router for Coder management.

    This router provides administrative endpoints that require admin permissions.

    Args:
        prefix: URL prefix
        tags: OpenAPI tags
        get_current_principal: Dependency to get current Principal (permissions)
        require_admin: Optional dependency to require admin role
        dependencies: Router dependencies (e.g., admin auth check)

    Returns:
        Configured APIRouter instance

    Example:
        ```python
        from computor_coder import create_admin_coder_router
        from computor_backend.permissions.auth import get_current_principal
        from computor_backend.api.exceptions import ForbiddenException

        async def require_admin(
            permissions: Annotated[Principal, Depends(get_current_principal)]
        ):
            if not permissions.is_admin:
                raise ForbiddenException("Admin access required")
            return permissions

        admin_router = create_admin_coder_router(
            get_current_principal=get_current_principal,
            require_admin=require_admin,
        )
        app.include_router(admin_router)
        ```
    """
    router = APIRouter(
        prefix=prefix,
        tags=tags or ["coder-admin"],
        dependencies=dependencies or [],
    )

    async def require_coder_enabled(
        settings: Annotated[CoderSettings, Depends(get_coder_settings)],
    ) -> CoderSettings:
        if not settings.enabled:
            raise CoderDisabledError()
        return settings

    # Use require_admin if provided, otherwise use get_current_principal
    auth_dependency = require_admin or get_current_principal

    if auth_dependency:

        @router.post(
            "/users/{email}/provision",
            response_model=ProvisionResult,
            summary="[Admin] Provision workspace for any user",
        )
        async def admin_provision_workspace(
            email: str,
            request: WorkspaceProvisionRequest,
            permissions: Annotated[Any, Depends(auth_dependency)],
            full_name: Optional[str] = None,
            _settings: Annotated[CoderSettings, Depends(require_coder_enabled)] = None,
            client: Annotated[CoderClient, Depends(get_coder_client)] = None,
        ) -> ProvisionResult:
            """
            [Admin] Provision a workspace for any user.

            This endpoint allows admins to provision workspaces without
            being authenticated as that user.
            """
            _ = permissions  # Verified by auth_dependency
            try:
                return await client.provision_workspace(
                    user_email=email,
                    user_password=request.password,
                    full_name=full_name,
                    template=request.template,
                    workspace_name=request.workspace_name,
                )
            except Exception as e:
                raise _handle_coder_error(e)

        @router.delete(
            "/users/{username}",
            response_model=WorkspaceActionResponse,
            summary="[Admin] Delete a Coder user",
        )
        async def admin_delete_user(
            username: str,
            permissions: Annotated[Any, Depends(auth_dependency)],
            _settings: Annotated[CoderSettings, Depends(require_coder_enabled)],
            client: Annotated[CoderClient, Depends(get_coder_client)],
        ) -> WorkspaceActionResponse:
            """[Admin] Delete a Coder user and all their workspaces."""
            _ = permissions  # Verified by auth_dependency
            try:
                success = await client.delete_user(username)
                return WorkspaceActionResponse(
                    success=success,
                    message=f"User {username} deleted" if success else f"Failed to delete user {username}",
                )
            except Exception as e:
                raise _handle_coder_error(e)

    return router
