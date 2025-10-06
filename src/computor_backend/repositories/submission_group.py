"""
Submission group repository for direct database access with optional caching.

This module provides the SubmissionGroupRepository class that handles
all database operations for SubmissionGroup entities with transparent caching.
"""

from typing import List, Optional, Set
from sqlalchemy.orm import Session

from .base import BaseRepository
from ..model.course import SubmissionGroup


class SubmissionGroupRepository(BaseRepository[SubmissionGroup]):
    """
    Repository for SubmissionGroup entity database operations with optional caching.

    Caching is automatic when cache instance is provided to constructor.
    """

    def __init__(self, db: Session, cache=None):
        """
        Initialize submission group repository.

        Args:
            db: SQLAlchemy session
            cache: Optional Cache instance (enables transparent caching)
        """
        super().__init__(db, SubmissionGroup, cache)

    # ========================================================================
    # Cache configuration
    # ========================================================================

    @property
    def entity_type(self) -> str:
        """Entity type identifier for cache keys."""
        return "submission_group"

    def get_ttl(self) -> int:
        """Submission groups are actively worked on - use 10 minute TTL."""
        return 600  # 10 minutes

    def get_entity_tags(self, entity: SubmissionGroup) -> Set[str]:
        """
        Get cache tags for a submission group.

        Tags:
        - submission_group:{id} - The specific group
        - submission_group:list - All group listings
        - course_content:{content_id} - All groups for this content
        - submission_group:content:{content_id} - Content-specific groups
        - course:{course_id} - All groups in this course (if accessible)
        """
        tags = {
            f"submission_group:{entity.id}",
            "submission_group:list",
        }

        if entity.course_content_id:
            tags.add(f"course_content:{entity.course_content_id}")
            tags.add(f"submission_group:content:{entity.course_content_id}")

            # If course_content relationship is loaded, add course tag
            if hasattr(entity, 'course_content') and entity.course_content:
                if entity.course_content.course_id:
                    tags.add(f"course:{entity.course_content.course_id}")

        return tags

    def get_list_tags(self, **filters) -> Set[str]:
        """Get cache tags for list queries."""
        tags = {"submission_group:list"}

        if "course_content_id" in filters:
            tags.add(f"submission_group:content:{filters['course_content_id']}")
            tags.add(f"course_content:{filters['course_content_id']}")

        return tags

    # ========================================================================
    # Specialized queries (with caching if enabled)
    # ========================================================================

    def find_by_course_content(self, course_content_id: str) -> List[SubmissionGroup]:
        """
        Find all submission groups for a course content (cached if enabled).

        Args:
            course_content_id: Course content identifier

        Returns:
            List of submission groups for the content
        """
        return self.find_by(course_content_id=course_content_id)

    def find_by_member(self, course_member_id: str) -> List[SubmissionGroup]:
        """
        Find all submission groups a course member belongs to (cached if enabled).

        Args:
            course_member_id: Course member identifier

        Returns:
            List of submission groups the member belongs to
        """
        # Try cache if enabled
        if self._use_cache():
            key = self.cache.key(self.entity_type, f"member:{course_member_id}")
            cached = self.cache.get_by_key(key)
            if cached is not None:
                return [self._deserialize_entity(item) for item in cached]

        # Query DB through SubmissionGroupMember relationship
        from ..model.course import SubmissionGroupMember
        query = self.db.query(SubmissionGroup).join(
            SubmissionGroupMember,
            SubmissionGroupMember.submission_group_id == SubmissionGroup.id
        ).filter(
            SubmissionGroupMember.course_member_id == course_member_id
        )
        entities = query.all()

        # Cache if enabled
        if self._use_cache():
            key = self.cache.key(self.entity_type, f"member:{course_member_id}")
            serialized = [self._serialize_entity(e) for e in entities]
            self.cache.set_with_tags(
                key=key,
                payload=serialized,
                tags={
                    "submission_group:list",
                    f"course_member:{course_member_id}",
                    f"submission_group:member:{course_member_id}"
                },
                ttl=self.get_ttl()
            )

        return entities

    def find_active_groups(self) -> List[SubmissionGroup]:
        """
        Find all non-archived submission groups (cached if enabled).

        Returns:
            List of active submission groups
        """
        return self.find_by(archived_at=None)
