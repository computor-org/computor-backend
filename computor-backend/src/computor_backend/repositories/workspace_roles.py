"""
Repository for workspace role data access.

Queries User + UserRole tables scoped to _workspace_user and _workspace_maintainer roles.
"""

import logging
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import outerjoin

from computor_backend.model.auth import User
from computor_backend.model.role import UserRole

logger = logging.getLogger(__name__)

WORKSPACE_ROLES = {"_workspace_user", "_workspace_maintainer"}


def get_users_with_workspace_roles(db: Session) -> List[Tuple[User, str]]:
    """Get all users who have workspace roles, with their role_ids.

    Returns:
        List of (User, role_id) tuples, ordered by family_name, given_name.
    """
    return (
        db.query(User, UserRole.role_id)
        .join(UserRole, User.id == UserRole.user_id)
        .filter(UserRole.role_id.in_(WORKSPACE_ROLES))
        .order_by(User.family_name, User.given_name)
        .all()
    )


def get_all_users_with_workspace_roles(db: Session) -> List[Tuple[User, Optional[str]]]:
    """Get all non-service users with their workspace roles (if any).

    Uses a LEFT OUTER JOIN so users without workspace roles appear with role_id=None.

    Returns:
        List of (User, role_id|None) tuples, ordered by family_name, given_name.
    """
    return (
        db.query(User, UserRole.role_id)
        .outerjoin(
            UserRole,
            (User.id == UserRole.user_id) & (UserRole.role_id.in_(WORKSPACE_ROLES)),
        )
        .filter(User.is_service == False)
        .order_by(User.family_name, User.given_name)
        .all()
    )


def find_user_by_email(db: Session, email: str) -> Optional[User]:
    """Find a user by email address."""
    return db.query(User).filter(User.email == email).first()


def get_user_role(db: Session, user_id: str, role_id: str) -> Optional[UserRole]:
    """Get a specific user-role assignment."""
    return (
        db.query(UserRole)
        .filter(UserRole.user_id == user_id, UserRole.role_id == role_id)
        .first()
    )


def get_workspace_roles_for_user(db: Session, user_id: str) -> List[str]:
    """Get all workspace role_ids for a user."""
    rows = (
        db.query(UserRole.role_id)
        .filter(UserRole.user_id == user_id, UserRole.role_id.in_(WORKSPACE_ROLES))
        .all()
    )
    return [r.role_id for r in rows]


def create_user_role(db: Session, user_id: str, role_id: str) -> UserRole:
    """Create a user-role assignment."""
    user_role = UserRole(user_id=user_id, role_id=role_id)
    db.add(user_role)
    db.commit()
    return user_role


def delete_user_role(db: Session, user_role: UserRole) -> None:
    """Delete a user-role assignment."""
    db.delete(user_role)
    db.commit()
