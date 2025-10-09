"""Backend UserRole interface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.user_roles import (
    UserRoleInterface as UserRoleInterfaceBase,
    UserRoleQuery,
)
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.role import UserRole


class UserRoleInterface(UserRoleInterfaceBase, BackendEntityInterface):
    """Backend-specific UserRole interface with model attached."""

    model = UserRole
    endpoint = "user-roles"
    cache_ttl = 300

    @staticmethod
    def search(db: Session, query, params: Optional[UserRoleQuery]):
        """Apply search filters to user role query."""
        if params is None:
            return query

        if params.user_id is not None:
            query = query.filter(UserRole.user_id == params.user_id)
        if params.role_id is not None:
            query = query.filter(UserRole.role_id == params.role_id)

        return query
