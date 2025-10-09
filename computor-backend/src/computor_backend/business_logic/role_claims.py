"""Business logic for role claim operations."""
from typing import List
from sqlalchemy.orm import Session

from computor_backend.permissions.core import check_permissions
from computor_backend.permissions.principal import Principal
from computor_types.roles_claims import RoleClaimList, RoleClaimQuery
from computor_backend.model.role import RoleClaim
from computor_backend.interfaces import RoleClaimInterface


def list_role_claims(
    permissions: Principal,
    role_claim_query: RoleClaimQuery,
    db: Session
) -> List[RoleClaimList]:
    """List role claims with permission check.

    Args:
        permissions: Current user permissions
        role_claim_query: Query parameters
        db: Database session

    Returns:
        List of role claims
    """
    query = check_permissions(permissions, RoleClaim, "get", db)
    return RoleClaimInterface.search(db, query, role_claim_query).all()
