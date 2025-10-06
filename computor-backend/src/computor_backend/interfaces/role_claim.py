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
        """Apply search filters to role claim query."""
        if params is None:
            return query

        if params.role_id is not None:
            query = query.filter(RoleClaim.role_id == params.role_id)
        if params.claim_type is not None:
            query = query.filter(RoleClaim.claim_type == params.claim_type)
        if params.claim_value is not None:
            query = query.filter(RoleClaim.claim_value == params.claim_value)

        return query
