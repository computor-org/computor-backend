"""
Backend-specific base interface that extends computor-types EntityInterface
with database and API concerns.
"""

from dataclasses import dataclass
from typing import Any, Iterable, List, Optional, Tuple

from sqlalchemy.orm import Session

from computor_types.base import EntityInterface as EntityInterfaceBase, ACTIONS


# Foreign keys that the default ``cache_invalidation_tags`` implementation
# treats as user-view tag carriers. Sticking the list here keeps the rule
# discoverable: any entity that grows one of these FKs automatically
# participates in cache invalidation without needing a per-interface override.
_DEFAULT_TAG_FKS = ("user_id", "course_id", "organization_id", "course_family_id")


@dataclass(frozen=True)
class CacheTag:
    """A single user-view cache tag to invalidate.

    Mirrors the kwargs accepted by ``Cache.invalidate_user_views``: either
    a ``user_id`` (matches the ``user:<id>`` tag) or an
    ``(entity_type, entity_id)`` pair (matches arbitrary entity tags).
    """
    user_id: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None

    @classmethod
    def for_user(cls, user_id) -> "CacheTag":
        return cls(user_id=str(user_id))

    @classmethod
    def for_entity(cls, entity_type: str, entity_id) -> "CacheTag":
        return cls(entity_type=entity_type, entity_id=str(entity_id))


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

    @classmethod
    def cache_invalidation_tags(cls, entity) -> Iterable[CacheTag]:
        """Yield user-view cache tags to invalidate when ``entity`` changes.

        Default behaviour: emit a tag for each of the standard scope
        foreign keys (``user_id``, ``course_id``, ``organization_id``,
        ``course_family_id``) the entity carries. Subclasses override
        when an entity needs additional tags — typically role-aware view
        tags like ``lecturer_view:<course_id>`` — and usually call
        ``super().cache_invalidation_tags(entity)`` to keep the default
        FK-based tags too.
        """
        for fk in _DEFAULT_TAG_FKS:
            value = getattr(entity, fk, None)
            if value is None:
                continue
            if fk == "user_id":
                yield CacheTag.for_user(value)
            else:
                yield CacheTag.for_entity(fk, value)
