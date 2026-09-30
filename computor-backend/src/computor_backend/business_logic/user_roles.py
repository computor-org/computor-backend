"""Business logic for user roles management."""
import logging
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import exc

from computor_backend.exceptions import (
    ForbiddenException,
    NotFoundException,
    InternalServerException,
)
from computor_backend.permissions.core import check_permissions
from computor_backend.permissions.principal import Principal
from computor_backend.permissions.roles import grants_system_admin
from computor_backend.model.role import UserRole

logger = logging.getLogger(__name__)


def get_user_role(
    user_id: UUID | str,
    role_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> UserRole:
    """Get a specific user role by user_id and role_id."""

    query = check_permissions(permissions, UserRole, "get", db)
    entity = query.filter(UserRole.user_id == user_id, UserRole.role_id == role_id).first()

    if not entity:
        raise NotFoundException(
            detail="UserRole not found",
            context={"user_id": str(user_id), "role_id": str(role_id)},
        )

    return entity


def delete_user_role(
    user_id: UUID | str,
    role_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> dict:
    """Delete a user role."""

    # The permission-filtered query below hides admin rows from
    # non-admins, which would turn this deliberate denial into a
    # confusing "UserRole not found". Admin membership is openly
    # readable, so name the real reason instead (issue #403).
    if not permissions.is_admin and grants_system_admin(str(role_id)):
        raise ForbiddenException(
            error_code="AUTHZ_005",
            detail="Only administrators can remove the admin role",
            context={"user_id": str(user_id), "role_id": str(role_id)},
        )

    query = check_permissions(permissions, UserRole, "delete", db)

    entity = query.filter(UserRole.user_id == user_id, UserRole.role_id == role_id).first()

    if not entity:
        raise NotFoundException(detail=f"{UserRole.__name__} not found")

    try:
        db.delete(entity)
        db.commit()
    except exc.SQLAlchemyError as e:
        db.rollback()
        logger.exception("Database error deleting user role")
        raise InternalServerException(detail="Failed to delete user role") from e

    return {"ok": True}
