"""
Backend-specific base interface that extends computor-types EntityInterface
with database and API concerns.
"""

from typing import Any, List, Tuple, Optional
from sqlalchemy.orm import Session
from computor_types.base import EntityInterface as EntityInterfaceBase, ACTIONS


class BackendEntityInterface(EntityInterfaceBase):
    """
    Backend-specific interface that adds SQLAlchemy model and API routing concerns
    to the pure DTO interface from computor-types.

    Attributes:
        model: SQLAlchemy model class
        endpoint: API endpoint path (e.g., "users", "courses")
        cache_ttl: Cache time-to-live in seconds
        search: Search function for filtering queries
        post_create: Hook called after entity creation
        post_update: Hook called after entity update
    """

    # Backend-specific attributes
    model: Any = None
    endpoint: str = None
    cache_ttl: int = 15
    search: Any = None
    post_create: Any = None
    post_update: Any = None

    # Custom permission check - when set, replaces generic check_permissions for updates
    # Signature: (permissions: Principal, db: Session, id: UUID, entity: BaseModel) -> Query
    # Should raise ForbiddenException if permission denied, return filtered query otherwise
    custom_permissions: Any = None

    @classmethod
    def claim_values(cls) -> List[Tuple[str, str]]:
        """
        Generate permission claims for this interface.

        Returns:
            List of (claim_type, claim_value) tuples for permissions
        """
        claims = []

        if cls.model is None:
            # Cannot generate claims without model
            return claims

        tablename = cls.model.__tablename__

        for attr, action in ACTIONS.items():
            if hasattr(cls, attr) and getattr(cls, attr) is not None:
                claims.append(("permissions", f"{tablename}:{action}"))

        return claims
