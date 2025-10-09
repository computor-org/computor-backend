"""
CourseContent repository for database access with cache invalidation.

This module provides the CourseContentRepository class that handles
all database operations for CourseContent entities with automatic cache invalidation.
"""

from typing import List, Optional, Set
from uuid import UUID
from sqlalchemy.orm import Session

from .base import BaseRepository
from ..model.course import CourseContent


class CourseContentRepository(BaseRepository[CourseContent]):
    """
    Repository for CourseContent entity with automatic cache invalidation.

    Handles course content CRUD operations and ensures all related caches
    (student views, tutor views, lecturer views) are properly invalidated.
    """

    def __init__(self, db: Session, cache=None):
        """
        Initialize course content repository.

        Args:
            db: SQLAlchemy session
            cache: Optional Cache instance (enables transparent caching)
        """
        super().__init__(db, CourseContent, cache)

    # ========================================================================
    # Cache configuration
    # ========================================================================

    @property
    def entity_type(self) -> str:
        """Entity type identifier for cache keys."""
        return "course_content"

    def get_ttl(self) -> int:
        """Course content changes frequently - use 10 minute TTL."""
        return 600  # 10 minutes

    def get_entity_tags(self, entity: CourseContent) -> Set[str]:
        """
        Get cache tags for course content.

        Tags:
        - course_content:{id} - The specific content
        - course_content:list - All content list queries
        - course:{course_id} - Invalidate course-level caches
        - student_view:{course_id} - Invalidate student views
        - tutor_view:{course_id} - Invalidate tutor views
        - lecturer_view:{course_id} - Invalidate lecturer views
        """
        tags = {
            f"course_content:{entity.id}",
            "course_content:list",
        }

        if entity.course_id:
            tags.add(f"course_content:course:{entity.course_id}")
            tags.add(f"course:{entity.course_id}")
            # Invalidate all view caches for this course
            tags.add(f"student_view:{entity.course_id}")
            tags.add(f"tutor_view:{entity.course_id}")
            tags.add(f"lecturer_view:{entity.course_id}")

        return tags

    def get_list_tags(self, **filters) -> Set[str]:
        """Get cache tags for list queries."""
        tags = {"course_content:list"}

        if "course_id" in filters:
            tags.add(f"course_content:course:{filters['course_id']}")
            tags.add(f"course:{filters['course_id']}")

        return tags

    # ========================================================================
    # Specialized queries
    # ========================================================================

    def find_by_course(self, course_id: str | UUID) -> List[CourseContent]:
        """
        Find all course content in a course.

        Args:
            course_id: Course identifier

        Returns:
            List of course content in the course
        """
        return self.find_by(course_id=str(course_id))

    def find_active_by_course(self, course_id: str | UUID) -> List[CourseContent]:
        """
        Find all non-archived course content in a course.

        Args:
            course_id: Course identifier

        Returns:
            List of active course content
        """
        query = self.db.query(CourseContent).filter(
            CourseContent.course_id == str(course_id),
            CourseContent.archived_at.is_(None)
        )
        return query.all()

    def find_by_parent(self, parent_id: str | UUID) -> List[CourseContent]:
        """
        Find all child content of a parent.

        Args:
            parent_id: Parent content identifier

        Returns:
            List of child content
        """
        return self.find_by(parent_id=str(parent_id))

    def find_submittable_by_course(self, course_id: str | UUID) -> List[CourseContent]:
        """
        Find all submittable content in a course.

        Args:
            course_id: Course identifier

        Returns:
            List of submittable course content
        """
        from ..model.course import CourseContentType, CourseContentKind

        query = (
            self.db.query(CourseContent)
            .join(CourseContentType)
            .join(CourseContentKind)
            .filter(
                CourseContent.course_id == str(course_id),
                CourseContent.archived_at.is_(None),
                CourseContentKind.submittable == True
            )
        )
        return query.all()

    def archive(self, entity_id: str | UUID) -> CourseContent:
        """
        Archive a course content (soft delete).

        Args:
            entity_id: Content identifier

        Returns:
            Updated content entity

        Raises:
            NotFoundError: If content not found
        """
        from datetime import datetime, timezone

        return self.update(
            str(entity_id),
            {"archived_at": datetime.now(timezone.utc)}
        )

    def unarchive(self, entity_id: str | UUID) -> CourseContent:
        """
        Unarchive a course content.

        Args:
            entity_id: Content identifier

        Returns:
            Updated content entity

        Raises:
            NotFoundError: If content not found
        """
        return self.update(str(entity_id), {"archived_at": None})
