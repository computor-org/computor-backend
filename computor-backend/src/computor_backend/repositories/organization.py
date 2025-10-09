"""
Organization repository for direct database access with optional caching.

This module provides the OrganizationRepository class that handles
all database operations for Organization entities with transparent caching.
"""

from typing import List, Optional, Set
from sqlalchemy.orm import Session
from ..custom_types import Ltree

from .base import BaseRepository
from ..model.organization import Organization


class OrganizationRepository(BaseRepository[Organization]):
    """
    Repository for Organization entity database operations with optional caching.

    Caching is automatic when cache instance is provided to constructor.
    """

    def __init__(self, db: Session, cache=None):
        """
        Initialize organization repository.

        Args:
            db: SQLAlchemy session
            cache: Optional Cache instance (enables transparent caching)
        """
        super().__init__(db, Organization, cache)

    # ========================================================================
    # Cache configuration
    # ========================================================================

    @property
    def entity_type(self) -> str:
        """Entity type identifier for cache keys."""
        return "organization"

    def get_ttl(self) -> int:
        """Organizations change infrequently - use 1 hour TTL."""
        return 3600  # 1 hour

    def get_entity_tags(self, entity: Organization) -> Set[str]:
        """
        Get cache tags for an organization.

        Tags:
        - org:{id} - The specific organization
        - org:list - All organization list queries
        - org:parent:{parent_path} - All children of a parent (if has parent)
        - org:type:{type} - Organizations of specific type
        """
        tags = {
            f"org:{entity.id}",
            "org:list",
            f"org:type:{entity.organization_type}"
        }

        if entity.parent_path:
            tags.add(f"org:parent:{entity.parent_path}")

        if entity.user_id:
            tags.add(f"user:{entity.user_id}")
            tags.add(f"org:user:{entity.user_id}")

        return tags

    def get_list_tags(self, **filters) -> Set[str]:
        """Get cache tags for list queries."""
        tags = {"org:list"}

        if "organization_type" in filters:
            tags.add(f"org:type:{filters['organization_type']}")

        if "user_id" in filters:
            tags.add(f"org:user:{filters['user_id']}")
            tags.add(f"user:{filters['user_id']}")

        return tags

    # ========================================================================
    # Specialized queries (with caching if enabled)
    # ========================================================================
    
    def find_by_path(self, path: str) -> Optional[Organization]:
        """
        Find organization by hierarchical path (cached if enabled).

        Args:
            path: The ltree path to search for

        Returns:
            Organization if found, None otherwise
        """
        # Try cache if enabled
        if self._use_cache():
            key = self.cache.key(self.entity_type, f"path:{path}")
            cached = self.cache.get_by_key(key)
            if cached is not None:
                return self._deserialize_entity(cached)

        # Query DB
        entity = self.db.query(Organization).filter(
            Organization.path == Ltree(path)
        ).first()

        # Cache if found and caching enabled
        if entity and self._use_cache():
            key = self.cache.key(self.entity_type, f"path:{path}")
            tags = self.get_entity_tags(entity)
            tags.add(f"org:path:{path}")
            self.cache.set_with_tags(
                key=key,
                payload=self._serialize_entity(entity),
                tags=tags,
                ttl=self.get_ttl()
            )

        return entity
    
    def find_by_organization_type(self, org_type: str) -> List[Organization]:
        """
        Find organizations by type.
        
        Args:
            org_type: Organization type ('user', 'community', 'organization')
            
        Returns:
            List of organizations of the specified type
        """
        return self.find_by(organization_type=org_type)
    
    def find_by_user_id(self, user_id: str) -> Optional[Organization]:
        """
        Find user organization by user ID.
        
        Args:
            user_id: The user identifier
            
        Returns:
            Organization if found, None otherwise
        """
        return self.find_one_by(user_id=user_id)
    
    def find_children(self, parent_path: str) -> List[Organization]:
        """
        Find all child organizations under a parent path (cached if enabled).

        Args:
            parent_path: The parent path to search under

        Returns:
            List of child organizations
        """
        # Try cache if enabled
        if self._use_cache():
            key = self.cache.key(self.entity_type, f"children:{parent_path}")
            cached = self.cache.get_by_key(key)
            if cached is not None:
                return [self._deserialize_entity(item) for item in cached]

        # Query DB
        query = self.db.query(Organization).filter(
            Organization.path.descendant_of(Ltree(parent_path))
        )
        entities = query.all()

        # Cache if enabled
        if self._use_cache():
            key = self.cache.key(self.entity_type, f"children:{parent_path}")
            serialized = [self._serialize_entity(e) for e in entities]
            self.cache.set_with_tags(
                key=key,
                payload=serialized,
                tags={f"org:parent:{parent_path}", "org:list"},
                ttl=self.get_ttl()
            )

        return entities

    def find_direct_children(self, parent_path: str) -> List[Organization]:
        """
        Find direct child organizations (immediate children only, cached if enabled).

        Args:
            parent_path: The parent path to search under

        Returns:
            List of direct child organizations
        """
        # Try cache if enabled
        if self._use_cache():
            key = self.cache.key(self.entity_type, f"direct_children:{parent_path}")
            cached = self.cache.get_by_key(key)
            if cached is not None:
                return [self._deserialize_entity(item) for item in cached]

        # Query DB
        query = self.db.query(Organization).filter(
            Organization.parent_path == Ltree(parent_path)
        )
        entities = query.all()

        # Cache if enabled
        if self._use_cache():
            key = self.cache.key(self.entity_type, f"direct_children:{parent_path}")
            serialized = [self._serialize_entity(e) for e in entities]
            self.cache.set_with_tags(
                key=key,
                payload=serialized,
                tags={f"org:parent:{parent_path}", "org:list"},
                ttl=self.get_ttl()
            )

        return entities
    
    def find_by_path_pattern(self, pattern: str) -> List[Organization]:
        """
        Find organizations matching a path pattern.
        
        Args:
            pattern: Ltree pattern to match (e.g., '*.university.*')
            
        Returns:
            List of organizations matching the pattern
        """
        query = self.db.query(Organization).filter(
            Organization.path.lquery(pattern)
        )
        return query.all()
    
    def find_active_organizations(self) -> List[Organization]:
        """
        Find all non-archived organizations.
        
        Returns:
            List of active (non-archived) organizations
        """
        return self.find_by(archived_at=None)
    
    def find_by_number(self, number: str) -> Optional[Organization]:
        """
        Find organization by number/identifier.
        
        Args:
            number: Organization number to search for
            
        Returns:
            Organization if found, None otherwise
        """
        return self.find_one_by(number=number)
    
    def search_by_title(self, title_pattern: str) -> List[Organization]:
        """
        Search organizations by title pattern (cached with shorter TTL).

        Args:
            title_pattern: Pattern to search for in titles

        Returns:
            List of organizations with matching titles
        """
        # Try cache if enabled
        if self._use_cache():
            key = self.cache.key(self.entity_type, f"search:{title_pattern}")
            cached = self.cache.get_by_key(key)
            if cached is not None:
                return [self._deserialize_entity(item) for item in cached]

        # Query DB
        query = self.db.query(Organization).filter(
            Organization.title.ilike(f"%{title_pattern}%")
        )
        entities = query.all()

        # Cache with shorter TTL (5 minutes) for search results
        if self._use_cache():
            key = self.cache.key(self.entity_type, f"search:{title_pattern}")
            serialized = [self._serialize_entity(e) for e in entities]
            self.cache.set_with_tags(
                key=key,
                payload=serialized,
                tags={"org:list", "org:search"},
                ttl=300  # 5 minutes for search results
            )

        return entities

    def get_root_organizations(self) -> List[Organization]:
        """
        Get all root organizations (cached if enabled).

        Returns:
            List of root organizations
        """
        # Try cache if enabled
        if self._use_cache():
            key = self.cache.key(self.entity_type, "roots")
            cached = self.cache.get_by_key(key)
            if cached is not None:
                return [self._deserialize_entity(item) for item in cached]

        # Query DB
        query = self.db.query(Organization).filter(
            Organization.parent_path.is_(None)
        )
        entities = query.all()

        # Cache if enabled
        if self._use_cache():
            key = self.cache.key(self.entity_type, "roots")
            serialized = [self._serialize_entity(e) for e in entities]
            self.cache.set_with_tags(
                key=key,
                payload=serialized,
                tags={"org:list", "org:roots"},
                ttl=self.get_ttl()
            )

        return entities