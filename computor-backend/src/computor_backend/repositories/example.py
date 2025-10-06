"""
Example repository for direct database access with optional caching.

This module provides the ExampleRepository class that handles
all database operations for Example entities with transparent caching.
"""

from typing import List, Optional, Set
from sqlalchemy.orm import Session

from .base import BaseRepository
from ..model.example import Example


class ExampleRepository(BaseRepository[Example]):
    """
    Repository for Example entity database operations with optional caching.

    Caching is automatic when cache instance is provided to constructor.
    """

    def __init__(self, db: Session, cache=None):
        """
        Initialize example repository.

        Args:
            db: SQLAlchemy session
            cache: Optional Cache instance (enables transparent caching)
        """
        super().__init__(db, Example, cache)

    # ========================================================================
    # Cache configuration
    # ========================================================================

    @property
    def entity_type(self) -> str:
        """Entity type identifier for cache keys."""
        return "example"

    def get_ttl(self) -> int:
        """Examples are relatively stable templates - use 1 hour TTL."""
        return 3600  # 1 hour

    def get_entity_tags(self, entity: Example) -> Set[str]:
        """
        Get cache tags for an example.

        Tags:
        - example:{id} - The specific example
        - example:list - All example listings
        - example:language:{language} - Examples for this language
        - example:public:{is_public} - Filter by public status
        """
        tags = {
            f"example:{entity.id}",
            "example:list",
        }

        if entity.language:
            tags.add(f"example:language:{entity.language}")

        if hasattr(entity, 'is_public') and entity.is_public is not None:
            tags.add(f"example:public:{entity.is_public}")

        return tags

    def get_list_tags(self, **filters) -> Set[str]:
        """Get cache tags for list queries."""
        tags = {"example:list"}

        if "language" in filters:
            tags.add(f"example:language:{filters['language']}")

        if "is_public" in filters:
            tags.add(f"example:public:{filters['is_public']}")

        return tags

    # ========================================================================
    # Specialized queries (with caching if enabled)
    # ========================================================================

    def find_by_language(self, language: str) -> List[Example]:
        """
        Find all examples for a programming language (cached if enabled).

        Args:
            language: Programming language identifier

        Returns:
            List of examples for the language
        """
        return self.find_by(language=language)

    def find_public_examples(self) -> List[Example]:
        """
        Find all public examples (cached if enabled).

        Returns:
            List of public examples
        """
        return self.find_by(is_public=True)

    def find_active_examples(self) -> List[Example]:
        """
        Find all non-archived examples (cached if enabled).

        Returns:
            List of active examples
        """
        return self.find_by(archived_at=None)

    def search_by_title(self, title_pattern: str) -> List[Example]:
        """
        Search examples by title pattern (cached with shorter TTL).

        Args:
            title_pattern: Pattern to search for in titles

        Returns:
            List of examples with matching titles
        """
        # Try cache if enabled
        if self._use_cache():
            key = self.cache.key(self.entity_type, f"search:{title_pattern}")
            cached = self.cache.get_by_key(key)
            if cached is not None:
                return [self._deserialize_entity(item) for item in cached]

        # Query DB
        query = self.db.query(Example).filter(
            Example.title.ilike(f"%{title_pattern}%")
        )
        entities = query.all()

        # Cache with shorter TTL (5 minutes) for search results
        if self._use_cache():
            key = self.cache.key(self.entity_type, f"search:{title_pattern}")
            serialized = [self._serialize_entity(e) for e in entities]
            self.cache.set_with_tags(
                key=key,
                payload=serialized,
                tags={"example:list", "example:search"},
                ttl=300  # 5 minutes for search results
            )

        return entities
