"""
Course member repository for direct database access with optional caching.

This module provides the CourseMemberRepository class that handles
all database operations for CourseMember entities with transparent caching.

IMPORTANT: This repository automatically invalidates permission caches
when memberships change, as course memberships are the foundation of
all permission checks in the system.
"""

from typing import List, Optional, Set
from sqlalchemy.orm import Session
import asyncio
import logging

from .base import BaseRepository
from ..model.course import CourseMember

logger = logging.getLogger(__name__)


class CourseMemberRepository(BaseRepository[CourseMember]):
    """
    Repository for CourseMember entity database operations with optional caching.

    Caching is automatic when cache instance is provided to constructor.

    CRITICAL SECURITY FEATURE:
    This repository automatically invalidates permission caches when
    memberships change, ensuring permission checks always reflect
    current membership status.
    """

    def __init__(self, db: Session, cache=None):
        """
        Initialize course member repository.

        Args:
            db: SQLAlchemy session
            cache: Optional Cache instance (enables transparent caching)
        """
        super().__init__(db, CourseMember, cache)

    # ========================================================================
    # Permission cache invalidation hooks
    # ========================================================================

    def _invalidate_permission_cache(self, entity: CourseMember) -> None:
        """
        Invalidate permission cache for a course member.

        This is CRITICAL for security - permission caches must be invalidated
        immediately when memberships change.
        """
        from ctutor_backend.permissions.cache import invalidate_user_course_memberships

        try:
            # Invalidate permission cache for this user
            asyncio.run(invalidate_user_course_memberships(str(entity.user_id)))
            logger.info(f"Invalidated permission cache for user {entity.user_id} (course {entity.course_id})")
        except Exception as e:
            # Log but don't fail the operation
            logger.warning(
                f"Failed to invalidate permission cache for user {entity.user_id}: {e}"
            )

    def create(self, entity: CourseMember) -> CourseMember:
        """
        Create a course member and invalidate permission caches.

        Args:
            entity: CourseMember to create

        Returns:
            Created CourseMember with ID populated
        """
        # Create via base repository (handles cache tags)
        result = super().create(entity)

        # Invalidate permission cache
        self._invalidate_permission_cache(result)

        return result

    def update(self, entity: CourseMember) -> CourseMember:
        """
        Update a course member and invalidate permission caches.

        Args:
            entity: CourseMember to update

        Returns:
            Updated CourseMember
        """
        # Update via base repository (handles cache tags)
        result = super().update(entity)

        # Invalidate permission cache
        self._invalidate_permission_cache(result)

        return result

    def delete(self, entity: CourseMember) -> None:
        """
        Delete a course member and invalidate permission caches.

        Args:
            entity: CourseMember to delete
        """
        # Store user_id before deletion
        user_id = entity.user_id

        # Delete via base repository (handles cache tags)
        super().delete(entity)

        # Invalidate permission cache
        from ctutor_backend.permissions.cache import invalidate_user_course_memberships
        try:
            asyncio.run(invalidate_user_course_memberships(str(user_id)))
            logger.info(f"Invalidated permission cache for user {user_id} after deletion")
        except Exception as e:
            logger.warning(
                f"Failed to invalidate permission cache for user {user_id}: {e}"
            )

    # ========================================================================
    # Cache configuration
    # ========================================================================

    @property
    def entity_type(self) -> str:
        """Entity type identifier for cache keys."""
        return "course_member"

    def get_ttl(self) -> int:
        """Course members change frequently (enrollment) - use 15 minute TTL."""
        return 900  # 15 minutes

    def get_entity_tags(self, entity: CourseMember) -> Set[str]:
        """
        Get cache tags for a course member.

        Tags:
        - course_member:{id} - The specific membership
        - course_member:list - All membership list queries
        - course:{course_id} - All members in this course
        - course_member:course:{course_id} - Course-specific membership queries
        - user:{user_id} - All memberships for this user
        - course_member:user:{user_id} - User-specific membership queries
        - course_member:role:{role} - Members with this role
        """
        tags = {
            f"course_member:{entity.id}",
            "course_member:list",
        }

        if entity.course_id:
            tags.add(f"course:{entity.course_id}")
            tags.add(f"course_member:course:{entity.course_id}")

        if entity.user_id:
            tags.add(f"user:{entity.user_id}")
            tags.add(f"course_member:user:{entity.user_id}")

        if entity.course_role_id:
            tags.add(f"course_member:role:{entity.course_role_id}")

        return tags

    def get_list_tags(self, **filters) -> Set[str]:
        """Get cache tags for list queries."""
        tags = {"course_member:list"}

        if "course_id" in filters:
            tags.add(f"course_member:course:{filters['course_id']}")
            tags.add(f"course:{filters['course_id']}")

        if "user_id" in filters:
            tags.add(f"course_member:user:{filters['user_id']}")
            tags.add(f"user:{filters['user_id']}")

        if "course_role_id" in filters:
            tags.add(f"course_member:role:{filters['course_role_id']}")

        return tags

    # ========================================================================
    # Specialized queries (with caching if enabled)
    # ========================================================================

    def find_by_course(self, course_id: str) -> List[CourseMember]:
        """
        Find all members in a course (cached if enabled).

        Args:
            course_id: Course identifier

        Returns:
            List of members in the course
        """
        return self.find_by(course_id=course_id)

    def find_by_user(self, user_id: str) -> List[CourseMember]:
        """
        Find all courses a user is enrolled in (cached if enabled).

        Args:
            user_id: User identifier

        Returns:
            List of user's course memberships
        """
        return self.find_by(user_id=user_id)

    def find_by_course_and_user(self, course_id: str, user_id: str) -> Optional[CourseMember]:
        """
        Find a specific user's membership in a course (cached if enabled).

        Args:
            course_id: Course identifier
            user_id: User identifier

        Returns:
            CourseMember if found, None otherwise
        """
        return self.find_one_by(course_id=course_id, user_id=user_id)

    def find_by_course_and_role(self, course_id: str, role: str) -> List[CourseMember]:
        """
        Find all members with a specific role in a course (cached if enabled).

        Args:
            course_id: Course identifier
            role: Course role ID (e.g., "_student", "_lecturer")

        Returns:
            List of members with the specified role
        """
        return self.find_by(course_id=course_id, course_role_id=role)

    def find_active_members(self) -> List[CourseMember]:
        """
        Find all non-archived course members (cached if enabled).

        Returns:
            List of active course members
        """
        return self.find_by(archived_at=None)
