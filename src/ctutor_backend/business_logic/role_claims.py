"""Business logic for role claim operations."""
from typing import List
from sqlalchemy.orm import Session

from ctutor_backend.permissions.core import check_permissions
from ctutor_backend.permissions.principal import Principal
from ctutor_backend.interface.roles_claims import RoleClaimList, RoleClaimQuery, role_claim_search
from ctutor_backend.model.role import RoleClaim


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
    return role_claim_search(db, query, role_claim_query).all()
