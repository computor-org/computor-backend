"""
Service repository for direct database access with optional caching.

This module provides the ServiceRepository class that handles
all database operations for Service entities with transparent caching.
"""

from typing import List, Optional, Set
from sqlalchemy.orm import Session

from .base import BaseRepository
from ..model.service import Service


class ServiceRepository(BaseRepository[Service]):
    """
    Repository for Service entity database operations with optional caching.

    Caching is automatic when cache instance is provided to constructor.
    """

    def __init__(self, db: Session, cache=None):
        """
        Initialize service repository.

        Args:
            db: SQLAlchemy session
            cache: Optional Cache instance (enables transparent caching)
        """
        super().__init__(db, Service, cache)

    # ========================================================================
    # Cache configuration
    # ========================================================================

    @property
    def entity_type(self) -> str:
        """Entity type identifier for cache keys."""
        return "service"

    def get_ttl(self) -> int:
        """Services change infrequently - use 30 minute TTL."""
        return 1800  # 30 minutes

    def get_entity_tags(self, entity: Service) -> Set[str]:
        """
        Get cache tags for a service.

        Tags:
        - service:{id} - The specific service
        - service:list - All service list queries
        - service:user:{user_id} - Service by user
        - service:slug:{slug} - Service by slug
        - service:type:{service_type_id} - Services of a type
        """
        tags = {
            f"service:{entity.id}",
            "service:list",
        }

        if entity.user_id:
            tags.add(f"service:user:{entity.user_id}")
            tags.add(f"user:{entity.user_id}")

        if entity.slug:
            tags.add(f"service:slug:{entity.slug}")

        if entity.service_type_id:
            tags.add(f"service:type:{entity.service_type_id}")

        return tags

    def get_list_tags(self, **filters) -> Set[str]:
        """Get cache tags for list queries."""
        tags = {"service:list"}

        if "user_id" in filters:
            tags.add(f"service:user:{filters['user_id']}")

        if "service_type_id" in filters:
            tags.add(f"service:type:{filters['service_type_id']}")

        if "enabled" in filters:
            tags.add(f"service:enabled:{filters['enabled']}")

        return tags

    # ========================================================================
    # Specialized queries (with caching if enabled)
    # ========================================================================

    def find_by_user_id(self, user_id: str) -> Optional[Service]:
        """
        Find service by user ID (1-to-1 relationship, cached if enabled).

        Args:
            user_id: User identifier

        Returns:
            Service if found, None otherwise
        """
        if self._use_cache():
            key = self.cache.key(self.entity_type, f"user:{user_id}")
            cached = self.cache.get_by_key(key)
            if cached is not None:
                return self._deserialize_entity(cached)

        entity = self.db.query(Service).filter(
            Service.user_id == user_id,
            Service.archived_at.is_(None)
        ).first()

        if entity and self._use_cache():
            key = self.cache.key(self.entity_type, f"user:{user_id}")
            tags = self.get_entity_tags(entity)
            self.cache.set_with_tags(
                key=key,
                payload=self._serialize_entity(entity),
                tags=tags,
                ttl=self.get_ttl()
            )

        return entity

    def find_by_slug(self, slug: str) -> Optional[Service]:
        """
        Find service by slug (cached if enabled).

        Args:
            slug: Service slug

        Returns:
            Service if found, None otherwise
        """
        if self._use_cache():
            key = self.cache.key(self.entity_type, f"slug:{slug}")
            cached = self.cache.get_by_key(key)
            if cached is not None:
                return self._deserialize_entity(cached)

        entity = self.db.query(Service).filter(
            Service.slug == slug,
            Service.archived_at.is_(None)
        ).first()

        if entity and self._use_cache():
            key = self.cache.key(self.entity_type, f"slug:{slug}")
            tags = self.get_entity_tags(entity)
            self.cache.set_with_tags(
                key=key,
                payload=self._serialize_entity(entity),
                tags=tags,
                ttl=self.get_ttl()
            )

        return entity

    def find_by_type(self, service_type_id: str) -> List[Service]:
        """
        Find all services of a given type (cached if enabled).

        Args:
            service_type_id: Service type identifier

        Returns:
            List of services of that type
        """
        if self._use_cache():
            key = self.cache.key(self.entity_type, f"type:{service_type_id}")
            cached = self.cache.get_by_key(key)
            if cached is not None:
                return [self._deserialize_entity(item) for item in cached]

        entities = self.db.query(Service).filter(
            Service.service_type_id == service_type_id,
            Service.archived_at.is_(None)
        ).all()

        if self._use_cache():
            key = self.cache.key(self.entity_type, f"type:{service_type_id}")
            serialized = [self._serialize_entity(e) for e in entities]
            self.cache.set_with_tags(
                key=key,
                payload=serialized,
                tags={f"service:type:{service_type_id}", "service:list"},
                ttl=self.get_ttl()
            )

        return entities

    def find_enabled(self) -> List[Service]:
        """
        Find all enabled services (cached if enabled).

        Returns:
            List of enabled, non-archived services
        """
        if self._use_cache():
            key = self.cache.key(self.entity_type, "enabled")
            cached = self.cache.get_by_key(key)
            if cached is not None:
                return [self._deserialize_entity(item) for item in cached]

        entities = self.db.query(Service).filter(
            Service.enabled == True,
            Service.archived_at.is_(None)
        ).all()

        if self._use_cache():
            key = self.cache.key(self.entity_type, "enabled")
            serialized = [self._serialize_entity(e) for e in entities]
            self.cache.set_with_tags(
                key=key,
                payload=serialized,
                tags={"service:enabled:True", "service:list"},
                ttl=self.get_ttl()
            )

        return entities

    def find_active(self) -> List[Service]:
        """
        Find all non-archived services.

        Returns:
            List of non-archived services
        """
        return self.find_by(archived_at=None)
