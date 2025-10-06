"""Backend RoleClaim interface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.roles_claims import (
    RoleClaimInterface as RoleClaimInterfaceBase,
    RoleClaimQuery,
)
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.role import RoleClaim


class RoleClaimInterface(RoleClaimInterfaceBase, BackendEntityInterface):
    """Backend-specific RoleClaim interface with model attached."""

    model = RoleClaim
    endpoint = "role-claims"
    cache_ttl = 600

    @staticmethod
    def search(db: Session, query, params: Optional[RoleClaimQuery]):
        """
        Apply search filters to roleclaim query.
        
        Note: Implement specific filters based on query parameters.
        This is a placeholder - update with actual filter logic.
        """
        # TODO: Implement search filters based on RoleClaimQuery fields
        return query
