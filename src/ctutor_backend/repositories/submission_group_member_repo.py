"""
SubmissionGroupMember repository for database access with cache invalidation.

This module provides the SubmissionGroupMemberRepository class that handles
all database operations for SubmissionGroupMember entities with automatic cache invalidation.
"""

from typing import List, Optional, Set
from uuid import UUID
from sqlalchemy.orm import Session

from .base import BaseRepository
from ..model.course import SubmissionGroupMember


class SubmissionGroupMemberRepository(BaseRepository[SubmissionGroupMember]):
    """
    Repository for SubmissionGroupMember entity with automatic cache invalidation.

    Handles submission group membership CRUD operations and ensures all related caches
    (group views, student views, member views) are properly invalidated.
    """

    def __init__(self, db: Session, cache=None):
        """
        Initialize submission group member repository.

        Args:
            db: SQLAlchemy session
            cache: Optional Cache instance (enables transparent caching)
        """
        super().__init__(db, SubmissionGroupMember, cache)

    # ========================================================================
    # Cache configuration
    # ========================================================================

    @property
    def entity_type(self) -> str:
        """Entity type identifier for cache keys."""
        return "submission_group_member"

    def get_ttl(self) -> int:
        """Group memberships are relatively stable - use 10 minute TTL."""
        return 600  # 10 minutes

    def get_entity_tags(self, entity: SubmissionGroupMember) -> Set[str]:
        """
        Get cache tags for submission group member.

        Tags:
        - submission_group_member:{id} - The specific membership
        - submission_group_member:list - All membership list queries
        - submission_group:{group_id} - Invalidate group-level caches
        - course_member:{member_id} - Invalidate member-level caches
        - submission_group_member:group:{group_id} - Members in this group
        - submission_group_member:member:{member_id} - Groups for this member
        - course:{course_id} - Invalidate course-level caches
        - student_view:{course_id} - Invalidate student views
        """
        tags = {
            f"submission_group_member:{entity.id}",
            "submission_group_member:list",
        }

        if entity.submission_group_id:
            tags.add(f"submission_group_member:group:{entity.submission_group_id}")
            tags.add(f"submission_group:{entity.submission_group_id}")

        if entity.course_member_id:
            tags.add(f"submission_group_member:member:{entity.course_member_id}")
            tags.add(f"course_member:{entity.course_member_id}")

        if entity.course_id:
            tags.add(f"course:{entity.course_id}")
            tags.add(f"student_view:{entity.course_id}")

        return tags

    def get_list_tags(self, **filters) -> Set[str]:
        """Get cache tags for list queries."""
        tags = {"submission_group_member:list"}

        if "submission_group_id" in filters:
            tags.add(f"submission_group_member:group:{filters['submission_group_id']}")
            tags.add(f"submission_group:{filters['submission_group_id']}")

        if "course_member_id" in filters:
            tags.add(f"submission_group_member:member:{filters['course_member_id']}")
            tags.add(f"course_member:{filters['course_member_id']}")

        if "course_id" in filters:
            tags.add(f"course:{filters['course_id']}")

        return tags

    # ========================================================================
    # Specialized queries
    # ========================================================================

    def find_by_group(self, group_id: str | UUID) -> List[SubmissionGroupMember]:
        """
        Find all members of a submission group.

        Args:
            group_id: Submission group identifier

        Returns:
            List of group members
        """
        return self.find_by(submission_group_id=str(group_id))

    def find_by_member(self, member_id: str | UUID) -> List[SubmissionGroupMember]:
        """
        Find all submission groups for a course member.

        Args:
            member_id: Course member identifier

        Returns:
            List of group memberships
        """
        return self.find_by(course_member_id=str(member_id))

    def find_by_course(self, course_id: str | UUID) -> List[SubmissionGroupMember]:
        """
        Find all submission group members in a course.

        Args:
            course_id: Course identifier

        Returns:
            List of all group memberships in the course
        """
        return self.find_by(course_id=str(course_id))

    def find_by_member_and_group(
        self,
        member_id: str | UUID,
        group_id: str | UUID
    ) -> Optional[SubmissionGroupMember]:
        """
        Find a specific group membership.

        Args:
            member_id: Course member identifier
            group_id: Submission group identifier

        Returns:
            SubmissionGroupMember if exists, None otherwise
        """
        return self.db.query(SubmissionGroupMember).filter(
            SubmissionGroupMember.course_member_id == str(member_id),
            SubmissionGroupMember.submission_group_id == str(group_id)
        ).first()

    def is_member_of_group(
        self,
        member_id: str | UUID,
        group_id: str | UUID
    ) -> bool:
        """
        Check if a member belongs to a group.

        Args:
            member_id: Course member identifier
            group_id: Submission group identifier

        Returns:
            True if member is in group, False otherwise
        """
        return self.find_by_member_and_group(member_id, group_id) is not None

    def get_group_size(self, group_id: str | UUID) -> int:
        """
        Get the number of members in a group.

        Args:
            group_id: Submission group identifier

        Returns:
            Number of members in the group
        """
        return self.db.query(SubmissionGroupMember).filter(
            SubmissionGroupMember.submission_group_id == str(group_id)
        ).count()
