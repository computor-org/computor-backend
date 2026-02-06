"""
ServiceType repository for direct database access with optional caching.

This module provides the ServiceTypeRepository class that handles
all database operations for ServiceType entities with transparent caching.
"""

from typing import List, Optional, Set
from sqlalchemy.orm import Session

from .base import BaseRepository
from ..model.service import ServiceType

try:
    from ..custom_types import Ltree
except ImportError:
    from computor_backend.custom_types import Ltree


class ServiceTypeRepository(BaseRepository[ServiceType]):
    """
    Repository for ServiceType entity database operations with optional caching.

    Caching is automatic when cache instance is provided to constructor.
    """

    def __init__(self, db: Session, cache=None):
        """
        Initialize service type repository.

        Args:
            db: SQLAlchemy session
            cache: Optional Cache instance (enables transparent caching)
        """
        super().__init__(db, ServiceType, cache)

    # ========================================================================
    # Cache configuration
    # ========================================================================

    @property
    def entity_type(self) -> str:
        """Entity type identifier for cache keys."""
        return "service_type"

    def get_ttl(self) -> int:
        """Service types rarely change - use 1 hour TTL."""
        return 3600  # 1 hour

    def get_entity_tags(self, entity: ServiceType) -> Set[str]:
        """
        Get cache tags for a service type.

        Tags:
        - service_type:{id} - The specific service type
        - service_type:list - All service type list queries
        - service_type:path:{path} - Service type by path
        - service_type:category:{category} - Service types by category
        """
        tags = {
            f"service_type:{entity.id}",
            "service_type:list",
        }

        if entity.path:
            tags.add(f"service_type:path:{entity.path}")

        if entity.category:
            tags.add(f"service_type:category:{entity.category}")

        return tags

    def get_list_tags(self, **filters) -> Set[str]:
        """Get cache tags for list queries."""
        tags = {"service_type:list"}

        if "category" in filters:
            tags.add(f"service_type:category:{filters['category']}")

        if "enabled" in filters:
            tags.add(f"service_type:enabled:{filters['enabled']}")

        return tags

    # ========================================================================
    # Specialized queries (with caching if enabled)
    # ========================================================================

    def find_by_path(self, path: str) -> Optional[ServiceType]:
        """
        Find service type by hierarchical path (cached if enabled).

        Args:
            path: The ltree path to search for (e.g., 'testing.python')

        Returns:
            ServiceType if found, None otherwise
        """
        if self._use_cache():
            key = self.cache.key(self.entity_type, f"path:{path}")
            cached = self.cache.get_by_key(key)
            if cached is not None:
                return self._deserialize_entity(cached)

        entity = self.db.query(ServiceType).filter(
            ServiceType.path == Ltree(path)
        ).first()

        if entity and self._use_cache():
            key = self.cache.key(self.entity_type, f"path:{path}")
            tags = self.get_entity_tags(entity)
            self.cache.set_with_tags(
                key=key,
                payload=self._serialize_entity(entity),
                tags=tags,
                ttl=self.get_ttl()
            )

        return entity

    def find_by_category(self, category: str) -> List[ServiceType]:
        """
        Find all service types in a category (cached if enabled).

        Args:
            category: Category name (e.g., 'testing', 'worker', 'review')

        Returns:
            List of service types in that category
        """
        if self._use_cache():
            key = self.cache.key(self.entity_type, f"category:{category}")
            cached = self.cache.get_by_key(key)
            if cached is not None:
                return [self._deserialize_entity(item) for item in cached]

        entities = self.db.query(ServiceType).filter(
            ServiceType.category == category
        ).all()

        if self._use_cache():
            key = self.cache.key(self.entity_type, f"category:{category}")
            serialized = [self._serialize_entity(e) for e in entities]
            self.cache.set_with_tags(
                key=key,
                payload=serialized,
                tags={f"service_type:category:{category}", "service_type:list"},
                ttl=self.get_ttl()
            )

        return entities

    def find_enabled(self) -> List[ServiceType]:
        """
        Find all enabled service types (cached if enabled).

        Returns:
            List of enabled service types
        """
        if self._use_cache():
            key = self.cache.key(self.entity_type, "enabled")
            cached = self.cache.get_by_key(key)
            if cached is not None:
                return [self._deserialize_entity(item) for item in cached]

        entities = self.db.query(ServiceType).filter(
            ServiceType.enabled == True
        ).all()

        if self._use_cache():
            key = self.cache.key(self.entity_type, "enabled")
            serialized = [self._serialize_entity(e) for e in entities]
            self.cache.set_with_tags(
                key=key,
                payload=serialized,
                tags={"service_type:enabled:True", "service_type:list"},
                ttl=self.get_ttl()
            )

        return entities

    def find_by_path_pattern(self, pattern: str) -> List[ServiceType]:
        """
        Find service types matching a path pattern.

        Args:
            pattern: Ltree pattern to match (e.g., 'testing.*')

        Returns:
            List of matching service types
        """
        return self.db.query(ServiceType).filter(
            ServiceType.path.lquery(pattern)
        ).all()
