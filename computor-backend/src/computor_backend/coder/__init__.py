"""
Coder integration for Computor platform.

This package provides workspace management via Coder, including:
- CoderClient: Async API client for Coder server
- CoderSettings: Configuration management
- Workspace provisioning and lifecycle management
- Token minting for workspace authentication
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
