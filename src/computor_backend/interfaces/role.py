"""Backend Role interface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.roles import (
    RoleInterface as RoleInterfaceBase,
    RoleQuery,
)
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.role import Role


class RoleInterface(RoleInterfaceBase, BackendEntityInterface):
    """Backend-specific Role interface with model attached."""

    model = Role
    endpoint = "roles"
    cache_ttl = 600

    @staticmethod
    def search(db: Session, query, params: Optional[RoleQuery]):
        """
        Apply search filters to role query.
        
        Note: Implement specific filters based on query parameters.
        This is a placeholder - update with actual filter logic.
        """
        # TODO: Implement search filters based on RoleQuery fields
        return query
