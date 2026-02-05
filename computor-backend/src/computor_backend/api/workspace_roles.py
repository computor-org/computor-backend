"""
API endpoints for workspace role management.

Thin router that delegates to business logic.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from computor_backend.database import get_db
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.business_logic.workspace_roles import (
    list_all_users,
    assign_workspace_role,
    remove_workspace_role,
)
from computor_types.workspace_roles import WorkspaceRoleAssign, WorkspaceRoleUser

workspace_roles_router = APIRouter()


@workspace_roles_router.get(
    "/users",
    response_model=list[WorkspaceRoleUser],
    summary="List all users with their workspace roles",
)
async def list_users(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """List all users. Each user includes their workspace roles (empty list if none)."""
    return list_all_users(permissions, db)


@workspace_roles_router.post(
    "/assign",
    response_model=WorkspaceRoleUser,
    summary="Assign a workspace role by email",
)
async def assign_role(
    body: WorkspaceRoleAssign,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Assign _workspace_user or _workspace_maintainer to a user by email."""
    return assign_workspace_role(permissions, body.email, body.role_id, db)


@workspace_roles_router.delete(
    "/users/{user_id}/{role_id}",
    summary="Remove a workspace role from a user",
)
async def remove_role(
    user_id: str,
    role_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Remove _workspace_user or _workspace_maintainer from a user."""
    return remove_workspace_role(permissions, user_id, role_id, db)
