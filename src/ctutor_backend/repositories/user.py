"""
User repository for direct database access with optional caching.

This module provides the UserRepository class that handles
all database operations for User entities with transparent caching.
"""

from typing import List, Optional, Set
from sqlalchemy.orm import Session

from .base import BaseRepository
from ..model.auth import User


class UserRepository(BaseRepository[User]):
    """
    Repository for User entity database operations with optional caching.

    Caching is automatic when cache instance is provided to constructor.
    """

    def __init__(self, db: Session, cache=None):
        """
        Initialize user repository.

        Args:
            db: SQLAlchemy session
            cache: Optional Cache instance (enables transparent caching)
        """
        super().__init__(db, User, cache)

    # ========================================================================
    # Cache configuration
    # ========================================================================

    @property
    def entity_type(self) -> str:
        """Entity type identifier for cache keys."""
        return "user"

    def get_ttl(self) -> int:
        """Users change infrequently - use 1 hour TTL."""
        return 3600  # 1 hour

    def get_entity_tags(self, entity: User) -> Set[str]:
        """
        Get cache tags for a user.

        Tags:
        - user:{id} - The specific user
        - user:list - All user list queries
        - user:email:{email} - Email-based lookups
        - user:username:{username} - Username-based lookups (if applicable)
        """
        tags = {
            f"user:{entity.id}",
            "user:list",
        }

        if entity.email:
            tags.add(f"user:email:{entity.email}")

        # Add username tag if user has a username field
        if hasattr(entity, 'username') and entity.username:
            tags.add(f"user:username:{entity.username}")

        return tags

    def get_list_tags(self, **filters) -> Set[str]:
        """Get cache tags for list queries."""
        tags = {"user:list"}

        if "email" in filters:
            tags.add(f"user:email:{filters['email']}")

        if "username" in filters and filters.get("username"):
            tags.add(f"user:username:{filters['username']}")

        return tags

    # ========================================================================
    # Specialized queries (with caching if enabled)
    # ========================================================================

    def find_by_email(self, email: str) -> Optional[User]:
        """
        Find user by email address (cached if enabled).

        Args:
            email: Email address to search for

        Returns:
            User if found, None otherwise
        """
        # Try cache if enabled
        if self._use_cache():
            key = self.cache.key(self.entity_type, f"email:{email}")
            cached = self.cache.get_by_key(key)
            if cached is not None:
                return self._deserialize_entity(cached)

        # Query DB
        entity = self.db.query(User).filter(
            User.email == email
        ).first()

        # Cache if found and caching enabled
        if entity and self._use_cache():
            key = self.cache.key(self.entity_type, f"email:{email}")
            tags = self.get_entity_tags(entity)
            tags.add(f"user:email:{email}")
            self.cache.set_with_tags(
                key=key,
                payload=self._serialize_entity(entity),
                tags=tags,
                ttl=self.get_ttl()
            )

        return entity

    def find_active_users(self) -> List[User]:
        """
        Find all non-archived users (cached if enabled).

        Returns:
            List of active users
        """
        return self.find_by(archived_at=None)

    def search_by_name(self, name_pattern: str) -> List[User]:
        """
        Search users by name pattern (given name or family name, cached with shorter TTL).

        Args:
            name_pattern: Pattern to search for in names

        Returns:
            List of users with matching names
        """
        # Try cache if enabled
        if self._use_cache():
            key = self.cache.key(self.entity_type, f"search:{name_pattern}")
            cached = self.cache.get_by_key(key)
            if cached is not None:
                return [self._deserialize_entity(item) for item in cached]

        # Query DB
        query = self.db.query(User).filter(
            (User.given_name.ilike(f"%{name_pattern}%")) |
            (User.family_name.ilike(f"%{name_pattern}%"))
        )
        entities = query.all()

        # Cache with shorter TTL (5 minutes) for search results
        if self._use_cache():
            key = self.cache.key(self.entity_type, f"search:{name_pattern}")
            serialized = [self._serialize_entity(e) for e in entities]
            self.cache.set_with_tags(
                key=key,
                payload=serialized,
                tags={"user:list", "user:search"},
                ttl=300  # 5 minutes for search results
            )

        return entities
