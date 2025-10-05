"""
Course repository for direct database access with optional caching.

This module provides the CourseRepository class that handles
all database operations for Course entities with transparent caching.
"""

from typing import List, Optional, Set
from sqlalchemy.orm import Session

from .base import BaseRepository
from ..model.course import Course


class CourseRepository(BaseRepository[Course]):
    """
    Repository for Course entity database operations with optional caching.

    Caching is automatic when cache instance is provided to constructor.
    """

    def __init__(self, db: Session, cache=None):
        """
        Initialize course repository.

        Args:
            db: SQLAlchemy session
            cache: Optional Cache instance (enables transparent caching)
        """
        super().__init__(db, Course, cache)

    # ========================================================================
    # Cache configuration
    # ========================================================================

    @property
    def entity_type(self) -> str:
        """Entity type identifier for cache keys."""
        return "course"

    def get_ttl(self) -> int:
        """Courses change moderately - use 30 minute TTL."""
        return 1800  # 30 minutes

    def get_entity_tags(self, entity: Course) -> Set[str]:
        """
        Get cache tags for a course.

        Tags:
        - course:{id} - The specific course
        - course:list - All course list queries
        - course:family:{family_id} - All courses in this family
        - course_family:{family_id} - Invalidate when family changes
        - org:{org_id} - Invalidate when organization changes (if accessible)
        """
        tags = {
            f"course:{entity.id}",
            "course:list",
        }

        if entity.course_family_id:
            tags.add(f"course:family:{entity.course_family_id}")
            tags.add(f"course_family:{entity.course_family_id}")

            # If course_family relationship is loaded, add org tag
            if hasattr(entity, 'course_family') and entity.course_family:
                if entity.course_family.organization_id:
                    tags.add(f"org:{entity.course_family.organization_id}")

        return tags

    def get_list_tags(self, **filters) -> Set[str]:
        """Get cache tags for list queries."""
        tags = {"course:list"}

        if "course_family_id" in filters:
            tags.add(f"course:family:{filters['course_family_id']}")

        return tags

    # ========================================================================
    # Specialized queries (with caching if enabled)
    # ========================================================================

    def find_by_course_family(self, course_family_id: str) -> List[Course]:
        """
        Find all courses in a course family (cached if enabled).

        Args:
            course_family_id: Course family identifier

        Returns:
            List of courses in the family
        """
        return self.find_by(course_family_id=course_family_id)

    def find_active_courses(self) -> List[Course]:
        """
        Find all non-archived courses (cached if enabled).

        Returns:
            List of active courses
        """
        return self.find_by(archived_at=None)

    def find_by_number(self, number: str) -> Optional[Course]:
        """
        Find course by number/code (cached if enabled).

        Args:
            number: Course number/code to search for

        Returns:
            Course if found, None otherwise
        """
        return self.find_one_by(number=number)

    def search_by_title(self, title_pattern: str) -> List[Course]:
        """
        Search courses by title pattern (cached with shorter TTL).

        Args:
            title_pattern: Pattern to search for in titles

        Returns:
            List of courses with matching titles
        """
        # Try cache if enabled
        if self._use_cache():
            key = self.cache.key(self.entity_type, f"search:{title_pattern}")
            cached = self.cache.get_by_key(key)
            if cached is not None:
                return [self._deserialize_entity(item) for item in cached]

        # Query DB
        query = self.db.query(Course).filter(
            Course.title.ilike(f"%{title_pattern}%")
        )
        entities = query.all()

        # Cache with shorter TTL (5 minutes) for search results
        if self._use_cache():
            key = self.cache.key(self.entity_type, f"search:{title_pattern}")
            serialized = [self._serialize_entity(e) for e in entities]
            self.cache.set_with_tags(
                key=key,
                payload=serialized,
                tags={"course:list", "course:search"},
                ttl=300  # 5 minutes for search results
            )

        return entities
