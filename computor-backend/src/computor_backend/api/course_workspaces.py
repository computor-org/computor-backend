"""Course-scoped workspace endpoints.

Workspace-maintainer-governed course configuration (allowed templates +
lecturer-provisioning flag) and the lecturer console for (throwaway) student
workspaces. Course roles get read access to the configuration; writes require
``workspace:manage``. See ``business_logic/course_workspaces.py`` for the
semantics.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from computor_backend.business_logic.course_workspaces import (
    delete_student_workspace,
    get_course_workspace_settings,
    list_student_workspaces,
    provision_student_workspaces,
    update_course_workspace_settings,
)
from computor_backend.coder.client import CoderClient, get_coder_client
from computor_backend.coder.config import CoderSettings, get_coder_settings
from computor_backend.database import get_db
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.redis_cache import get_cache
from computor_types.coder import WorkspaceActionResponse
from computor_types.course_workspaces import (
    CourseStudentWorkspacesResponse,
    CourseWorkspaceSettingsGet,
    CourseWorkspaceSettingsUpdate,
    StudentWorkspaceProvisionRequest,
    StudentWorkspaceProvisionResponse,
)

course_workspaces_router = APIRouter()


@course_workspaces_router.get(
    "/courses/{course_id}/workspace-settings",
    response_model=CourseWorkspaceSettingsGet,
)
async def get_course_workspace_settings_endpoint(
    course_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    client: Annotated[CoderClient, Depends(get_coder_client)],
    coder_settings: Annotated[CoderSettings, Depends(get_coder_settings)],
) -> CourseWorkspaceSettingsGet:
    """Course workspace configuration (members read, managers get the picker)."""
    return await get_course_workspace_settings(
        str(course_id), permissions, db, client, coder_settings
    )


@course_workspaces_router.put(
    "/courses/{course_id}/workspace-settings",
    response_model=CourseWorkspaceSettingsGet,
)
async def update_course_workspace_settings_endpoint(
    course_id: UUID | str,
    data: CourseWorkspaceSettingsUpdate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    client: Annotated[CoderClient, Depends(get_coder_client)],
    coder_settings: Annotated[CoderSettings, Depends(get_coder_settings)],
) -> CourseWorkspaceSettingsGet:
    """Replace the course's allowed templates and flags (workspace:manage)."""
    return await update_course_workspace_settings(
        str(course_id), data, permissions, db, client, coder_settings
    )


@course_workspaces_router.post(
    "/courses/{course_id}/student-workspaces/provision",
    response_model=StudentWorkspaceProvisionResponse,
)
async def provision_student_workspaces_endpoint(
    course_id: UUID | str,
    data: StudentWorkspaceProvisionRequest,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    cache: Annotated[object, Depends(get_cache)],
    client: Annotated[CoderClient, Depends(get_coder_client)],
    coder_settings: Annotated[CoderSettings, Depends(get_coder_settings)],
) -> StudentWorkspaceProvisionResponse:
    """Bulk-provision (throwaway) workspaces for selected course members."""
    return await provision_student_workspaces(
        str(course_id), data, permissions, db, cache, client, coder_settings
    )


@course_workspaces_router.get(
    "/courses/{course_id}/student-workspaces",
    response_model=CourseStudentWorkspacesResponse,
)
async def list_student_workspaces_endpoint(
    course_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    client: Annotated[CoderClient, Depends(get_coder_client)],
) -> CourseStudentWorkspacesResponse:
    """Course members' workspaces on course-allowed templates (lecturer view)."""
    return await list_student_workspaces(str(course_id), permissions, db, client)


@course_workspaces_router.delete(
    "/courses/{course_id}/student-workspaces/{username}/{workspace_name}",
    response_model=WorkspaceActionResponse,
)
async def delete_student_workspace_endpoint(
    course_id: UUID | str,
    username: str,
    workspace_name: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    client: Annotated[CoderClient, Depends(get_coder_client)],
) -> WorkspaceActionResponse:
    """Delete a member's throwaway workspace (lecturers: scratch-home only)."""
    return await delete_student_workspace(
        str(course_id), username, workspace_name, permissions, db, client
    )
