"""
Computor Coder - Workspace management plugin for Computor platform.

This package provides integration with Coder for managing development
workspaces. It includes:

- CoderClient: Async API client for Coder
- CoderPlugin: Service plugin for backend integration
- FastAPI routers for workspace endpoints
- Pydantic schemas for API contracts

Example usage:

    ```python
    from computor_coder import CoderPlugin, CoderClient

    # As a plugin (recommended for backend integration)
    coder = CoderPlugin()
    await coder.initialize()
    app.include_router(coder.get_router(...), prefix="/api/v1")

    # Direct client usage
    async with CoderClient() as client:
        result = await client.provision_workspace(
            user_email="user@example.com",
            user_password="password",
        )
    ```
"""

__version__ = "0.1.0"

# Client
from .client import (
    CoderClient,
    get_coder_client,
    reset_coder_client,
)

# Configuration
from .config import (
    CoderSettings,
    get_coder_settings,
    configure_coder_settings,
    reset_coder_settings,
)

# Exceptions
from .exceptions import (
    CoderError,
    CoderAPIError,
    CoderAuthenticationError,
    CoderConnectionError,
    CoderConflictError,
    CoderDisabledError,
    CoderNotFoundError,
    CoderPermissionError,
    CoderTemplateNotFoundError,
    CoderTimeoutError,
    CoderUserExistsError,
    CoderUserNotFoundError,
    CoderWorkspaceActionError,
    CoderWorkspaceExistsError,
    CoderWorkspaceNotFoundError,
)

# Plugin
from .plugin import (
    CoderPlugin,
    get_coder_plugin,
    initialize_coder_plugin,
    reset_coder_plugin,
)

# Router factory
from .router import (
    create_admin_coder_router,
    create_coder_router,
)

# Schemas
from .schemas import (
    CoderHealthResponse,
    CoderTemplate,
    CoderUser,
    CoderUserCreate,
    CoderWorkspace,
    CoderWorkspaceCreate,
    ProvisionResult,
    TemplateListResponse,
    WorkspaceActionResponse,
    WorkspaceDetails,
    WorkspaceListResponse,
    WorkspaceProvisionRequest,
    WorkspaceStatus,
    WorkspaceTemplate,
    WorkspaceBuildStatus,
)

__all__ = [
    # Version
    "__version__",
    # Client
    "CoderClient",
    "get_coder_client",
    "reset_coder_client",
    # Configuration
    "CoderSettings",
    "get_coder_settings",
    "configure_coder_settings",
    "reset_coder_settings",
    # Exceptions
    "CoderError",
    "CoderAPIError",
    "CoderAuthenticationError",
    "CoderConnectionError",
    "CoderConflictError",
    "CoderDisabledError",
    "CoderNotFoundError",
    "CoderPermissionError",
    "CoderTemplateNotFoundError",
    "CoderTimeoutError",
    "CoderUserExistsError",
    "CoderUserNotFoundError",
    "CoderWorkspaceActionError",
    "CoderWorkspaceExistsError",
    "CoderWorkspaceNotFoundError",
    # Plugin
    "CoderPlugin",
    "get_coder_plugin",
    "initialize_coder_plugin",
    "reset_coder_plugin",
    # Router
    "create_admin_coder_router",
    "create_coder_router",
    # Schemas
    "CoderHealthResponse",
    "CoderTemplate",
    "CoderUser",
    "CoderUserCreate",
    "CoderWorkspace",
    "CoderWorkspaceCreate",
    "ProvisionResult",
    "TemplateListResponse",
    "WorkspaceActionResponse",
    "WorkspaceDetails",
    "WorkspaceListResponse",
    "WorkspaceProvisionRequest",
    "WorkspaceStatus",
    "WorkspaceTemplate",
    "WorkspaceBuildStatus",
]
