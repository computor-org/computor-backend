"""Business logic for user roles management."""
import logging
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import exc

from computor_backend.exceptions import NotFoundException, InternalServerException
from computor_backend.permissions.core import check_permissions
from computor_backend.permissions.principal import Principal
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
        raise NotFoundException(detail=f"UserRole not found for user {user_id} and role {role_id}")

    return entity


def delete_user_role(
    user_id: UUID | str,
    role_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> dict:
    """Delete a user role."""

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
