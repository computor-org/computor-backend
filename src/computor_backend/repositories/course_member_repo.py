"""
CourseMember repository for database access with permission cache invalidation.

This module provides the CourseMemberRepository class that handles
all database operations for CourseMember entities with automatic
permission cache invalidation.
"""

from typing import List, Optional, Set
from uuid import UUID
from sqlalchemy.orm import Session
import asyncio

from .base import BaseRepository
from ..model.course import CourseMember


class CourseMemberRepository(BaseRepository[CourseMember]):
    """
    Repository for CourseMember entity with automatic permission cache invalidation.

    CRITICAL: This repository invalidates permission caches because course
    memberships are the foundation of all permission checks in the system.

    When a CourseMember is created/updated/deleted, all permission caches
    for that user must be invalidated.
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
    # Cache configuration
    # ========================================================================

    @property
    def entity_type(self) -> str:
        """Entity type identifier for cache keys."""
        return "course_member"

    def get_ttl(self) -> int:
        """Course memberships are relatively stable - use 10 minute TTL."""
        return 600  # 10 minutes

    def get_entity_tags(self, entity: CourseMember) -> Set[str]:
        """
        Get cache tags for course member.

        Tags:
        - course_member:{id} - The specific membership
        - course_member:list - All membership list queries
        - course:{course_id} - Invalidate course-level caches
        - user:{user_id} - Invalidate user-level caches
        - course_member:course:{course_id} - Members in this course
        - course_member:user:{user_id} - Memberships for this user
        - student_view:{course_id} - Invalidate student views
        - tutor_view:{course_id} - Invalidate tutor views
        - lecturer_view:{course_id} - Invalidate lecturer views
        """
        tags = {
            f"course_member:{entity.id}",
            "course_member:list",
        }

        if entity.course_id:
            tags.add(f"course_member:course:{entity.course_id}")
            tags.add(f"course:{entity.course_id}")
            tags.add(f"student_view:{entity.course_id}")
            tags.add(f"tutor_view:{entity.course_id}")
            tags.add(f"lecturer_view:{entity.course_id}")

        if entity.user_id:
            tags.add(f"course_member:user:{entity.user_id}")
            tags.add(f"user:{entity.user_id}")

        # Tag by role for role-specific queries
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
    # Permission cache invalidation hooks
    # ========================================================================

    def _invalidate_permission_cache(self, entity: CourseMember) -> None:
        """
        Invalidate permission cache for a course member.

        This is CRITICAL for security - permission caches must be invalidated
        immediately when memberships change.
        """
        from computor_backend.permissions.cache import invalidate_user_course_memberships

        try:
            # Invalidate permission cache for this user
            asyncio.run(invalidate_user_course_memberships(str(entity.user_id)))
        except Exception as e:
            # Log but don't fail the operation
            import logging
            logging.getLogger(__name__).warning(
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
        from computor_backend.permissions.cache import invalidate_user_course_memberships
        try:
            asyncio.run(invalidate_user_course_memberships(str(user_id)))
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                f"Failed to invalidate permission cache for user {user_id}: {e}"
            )

    # ========================================================================
    # Specialized queries
    # ========================================================================

    def find_by_course(self, course_id: str | UUID) -> List[CourseMember]:
        """
        Find all members of a course.

        Args:
            course_id: Course identifier

        Returns:
            List of course members
        """
        return self.find_by(course_id=str(course_id))

    def find_by_user(self, user_id: str | UUID) -> List[CourseMember]:
        """
        Find all course memberships for a user.

        Args:
            user_id: User identifier

        Returns:
            List of course memberships
        """
        return self.find_by(user_id=str(user_id))

    def find_by_course_and_user(
        self,
        course_id: str | UUID,
        user_id: str | UUID
    ) -> Optional[CourseMember]:
        """
        Find a specific course membership.

        Args:
            course_id: Course identifier
            user_id: User identifier

        Returns:
            CourseMember if exists, None otherwise
        """
        return self.db.query(CourseMember).filter(
            CourseMember.course_id == str(course_id),
            CourseMember.user_id == str(user_id)
        ).first()

    def find_by_role(self, course_id: str | UUID, role_id: str) -> List[CourseMember]:
        """
        Find all members with a specific role in a course.

        Args:
            course_id: Course identifier
            role_id: Course role identifier (e.g., "_student", "_tutor", "_lecturer")

        Returns:
            List of course members with this role
        """
        return self.db.query(CourseMember).filter(
            CourseMember.course_id == str(course_id),
            CourseMember.course_role_id == role_id
        ).all()

    def get_user_role_in_course(
        self,
        user_id: str | UUID,
        course_id: str | UUID
    ) -> Optional[str]:
        """
        Get the user's role in a specific course.

        Args:
            user_id: User identifier
            course_id: Course identifier

        Returns:
            Role ID if user is a member, None otherwise
        """
        member = self.find_by_course_and_user(course_id, user_id)
        return member.course_role_id if member else None

    def is_member(self, user_id: str | UUID, course_id: str | UUID) -> bool:
        """
        Check if a user is a member of a course.

        Args:
            user_id: User identifier
            course_id: Course identifier

        Returns:
            True if user is a member, False otherwise
        """
        return self.find_by_course_and_user(course_id, user_id) is not None

    def count_members(self, course_id: str | UUID) -> int:
        """
        Count the number of members in a course.

        Args:
            course_id: Course identifier

        Returns:
            Number of members
        """
        return self.db.query(CourseMember).filter(
            CourseMember.course_id == str(course_id)
        ).count()

    def count_by_role(self, course_id: str | UUID, role_id: str) -> int:
        """
        Count members with a specific role in a course.

        Args:
            course_id: Course identifier
            role_id: Course role identifier

        Returns:
            Number of members with this role
        """
        return self.db.query(CourseMember).filter(
            CourseMember.course_id == str(course_id),
            CourseMember.course_role_id == role_id
        ).count()
