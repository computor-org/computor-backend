"""
Course family repository for direct database access with optional caching.

This module provides the CourseFamilyRepository class that handles
all database operations for CourseFamily entities with transparent caching.
"""

from typing import List, Optional, Set
from sqlalchemy.orm import Session

from .base import BaseRepository
from ..model.course import CourseFamily


class CourseFamilyRepository(BaseRepository[CourseFamily]):
    """
    Repository for CourseFamily entity database operations with optional caching.

    Caching is automatic when cache instance is provided to constructor.
    """

    def __init__(self, db: Session, cache=None):
        """
        Initialize course family repository.

        Args:
            db: SQLAlchemy session
            cache: Optional Cache instance (enables transparent caching)
        """
        super().__init__(db, CourseFamily, cache)

    # ========================================================================
    # Cache configuration
    # ========================================================================

    @property
    def entity_type(self) -> str:
        """Entity type identifier for cache keys."""
        return "course_family"

    def get_ttl(self) -> int:
        """Course families change infrequently - use 1 hour TTL."""
        return 3600  # 1 hour

    def get_entity_tags(self, entity: CourseFamily) -> Set[str]:
        """
        Get cache tags for a course family.

        Tags:
        - course_family:{id} - The specific course family
        - course_family:list - All course family list queries
        - course_family:org:{org_id} - All families in this organization
        - org:{org_id} - Invalidate when organization changes
        """
        tags = {
            f"course_family:{entity.id}",
            "course_family:list",
        }

        if entity.organization_id:
            tags.add(f"course_family:org:{entity.organization_id}")
            tags.add(f"org:{entity.organization_id}")

        return tags

    def get_list_tags(self, **filters) -> Set[str]:
        """Get cache tags for list queries."""
        tags = {"course_family:list"}

        if "organization_id" in filters:
            tags.add(f"course_family:org:{filters['organization_id']}")

        return tags

    # ========================================================================
    # Specialized queries (with caching if enabled)
    # ========================================================================

    def find_by_organization(self, organization_id: str) -> List[CourseFamily]:
        """
        Find all course families in an organization (cached if enabled).

        Args:
            organization_id: Organization identifier

        Returns:
            List of course families in the organization
        """
        return self.find_by(organization_id=organization_id)

    def find_active_families(self) -> List[CourseFamily]:
        """
        Find all non-archived course families (cached if enabled).

        Returns:
            List of active course families
        """
        return self.find_by(archived_at=None)

    def find_by_number(self, number: str) -> Optional[CourseFamily]:
        """
        Find course family by number/code (cached if enabled).

        Args:
            number: Course family number/code to search for

        Returns:
            CourseFamily if found, None otherwise
        """
        return self.find_one_by(number=number)

    def search_by_title(self, title_pattern: str) -> List[CourseFamily]:
        """
        Search course families by title pattern (cached with shorter TTL).

        Args:
            title_pattern: Pattern to search for in titles

        Returns:
            List of course families with matching titles
        """
        # Try cache if enabled
        if self._use_cache():
            key = self.cache.key(self.entity_type, f"search:{title_pattern}")
            cached = self.cache.get_by_key(key)
            if cached is not None:
                return [self._deserialize_entity(item) for item in cached]

        # Query DB
        query = self.db.query(CourseFamily).filter(
            CourseFamily.title.ilike(f"%{title_pattern}%")
        )
        entities = query.all()

        # Cache with shorter TTL (5 minutes) for search results
        if self._use_cache():
            key = self.cache.key(self.entity_type, f"search:{title_pattern}")
            serialized = [self._serialize_entity(e) for e in entities]
            self.cache.set_with_tags(
                key=key,
                payload=serialized,
                tags={"course_family:list", "course_family:search"},
                ttl=300  # 5 minutes for search results
            )

        return entities
