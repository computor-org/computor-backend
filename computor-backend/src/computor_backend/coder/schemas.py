"""Re-export shim: the Coder API DTOs live in ``computor_types.coder``.

Kept so existing ``computor_backend.coder.schemas`` imports (client, API,
tests) stay valid; new code should import from ``computor_types.coder``.
"""

from computor_types.coder import (  # noqa: F401
    CoderAdminTaskListResponse,
    CoderAdminTaskResponse,
    CoderFleetStatusResponse,
    CoderHealthResponse,
    CoderTemplate,
    CoderTemplateFleetStatus,
    CoderUser,
    CoderUserCreate,
    CoderWorkspace,
    CoderWorkspaceCreate,
    ImageBuildRequest,
    ProvisionResult,
    TemplateFile,
    TemplateFileActionResponse,
    TemplateFileUpdateRequest,
    TemplateFilesResponse,
    TemplateListResponse,
    TemplatePushRequest,
    TemplateSettingsListResponse,
    TemplateVariable,
    TemplateVariablesResponse,
    WorkspaceActionResponse,
    WorkspaceBuildStatus,
    WorkspaceDetails,
    WorkspaceListResponse,
    WorkspaceRolloutRequest,
    WorkspaceStatus,
    WorkspaceTemplateSettingsSchema,
    WorkspaceTemplateSettingsUpdate,
)
