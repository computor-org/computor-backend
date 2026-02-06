"""
Business logic for workspace role management.

Handles permission checks and orchestrates repository calls for
assigning/removing _workspace_user and _workspace_maintainer roles.
"""

import logging
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from computor_backend.permissions.principal import Principal
from computor_backend.repositories.workspace_roles import (
    WORKSPACE_ROLES,
    get_all_users_with_workspace_roles,
    get_users_with_workspace_roles,
    find_user_by_email,
    get_user_role,
    get_workspace_roles_for_user,
    create_user_role,
    delete_user_role,
)
from computor_types.workspace_roles import WorkspaceRoleUser

logger = logging.getLogger(__name__)


def _require_manage(permissions: Principal) -> None:
    """Require workspace:manage permission (or admin)."""
    if permissions.is_admin:
        return
    if not permissions.permitted("workspace", "manage"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Workspace 'manage' permission required.",
        )


def list_all_users(
    permissions: Principal,
    db: Session,
) -> List[WorkspaceRoleUser]:
    """List all users with their workspace roles (if any).

    Returns every non-service user. Users without workspace roles
    have an empty roles list. Groups by user.
    """
    _require_manage(permissions)

    rows = get_all_users_with_workspace_roles(db)

    user_map: dict[str, WorkspaceRoleUser] = {}
    for user, role_id in rows:
        uid = str(user.id)
        if uid not in user_map:
            user_map[uid] = WorkspaceRoleUser(
                user_id=uid,
                email=user.email,
                username=user.username,
                given_name=user.given_name,
                family_name=user.family_name,
            )
        if role_id is not None:
            user_map[uid].roles.append(role_id)

    return list(user_map.values())


def assign_workspace_role(
    permissions: Principal,
    email: str,
    role_id: str,
    db: Session,
) -> WorkspaceRoleUser:
    """Assign a workspace role to a user by email.

    Validates the role_id, looks up the user, and creates the assignment.
    Returns the user with all their current workspace roles.
    """
    _require_manage(permissions)

    if role_id not in WORKSPACE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(sorted(WORKSPACE_ROLES))}",
        )

    user = find_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No user found with email: {email}",
        )

    existing = get_user_role(db, str(user.id), role_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User already has the {role_id} role",
        )

    create_user_role(db, str(user.id), role_id)

    all_roles = get_workspace_roles_for_user(db, str(user.id))

    return WorkspaceRoleUser(
        user_id=str(user.id),
        email=user.email,
        username=user.username,
        given_name=user.given_name,
        family_name=user.family_name,
        roles=all_roles,
    )


def remove_workspace_role(
    permissions: Principal,
    user_id: str,
    role_id: str,
    db: Session,
) -> dict:
    """Remove a workspace role from a user.

    Validates the role_id and deletes the assignment.
    """
    _require_manage(permissions)

    if role_id not in WORKSPACE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(sorted(WORKSPACE_ROLES))}",
        )

    user_role = get_user_role(db, user_id, role_id)
    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User role not found",
        )

    delete_user_role(db, user_role)

    return {"ok": True}
