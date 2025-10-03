"""
Submission artifact repository for direct database access with optional caching.

This module provides the SubmissionArtifactRepository class that handles
all database operations for SubmissionArtifact entities with transparent caching.
"""

from typing import List, Optional, Set
from sqlalchemy.orm import Session

from .base import BaseRepository
from ..model.artifact import SubmissionArtifact


class SubmissionArtifactRepository(BaseRepository[SubmissionArtifact]):
    """
    Repository for SubmissionArtifact entity database operations with optional caching.

    Caching is automatic when cache instance is provided to constructor.
    """

    def __init__(self, db: Session, cache=None):
        """
        Initialize submission artifact repository.

        Args:
            db: SQLAlchemy session
            cache: Optional Cache instance (enables transparent caching)
        """
        super().__init__(db, SubmissionArtifact, cache)

    # ========================================================================
    # Cache configuration
    # ========================================================================

    @property
    def entity_type(self) -> str:
        """Entity type identifier for cache keys."""
        return "submission_artifact"

    def get_ttl(self) -> int:
        """Artifacts are frequently created during active work - use 5 minute TTL."""
        return 300  # 5 minutes

    def get_entity_tags(self, entity: SubmissionArtifact) -> Set[str]:
        """
        Get cache tags for a submission artifact.

        Tags:
        - submission_artifact:{id} - The specific artifact
        - submission_artifact:list - All artifact listings
        - submission_group:{group_id} - All artifacts in this group
        - submission_artifact:group:{group_id} - Group-specific artifacts
        - course_member:{member_id} - All artifacts by this member
        - submission_artifact:member:{member_id} - Member-specific artifacts
        - submission_artifact:submit:{submit} - Filter by official submission status
        """
        tags = {
            f"submission_artifact:{entity.id}",
            "submission_artifact:list",
        }

        if entity.submission_group_id:
            tags.add(f"submission_group:{entity.submission_group_id}")
            tags.add(f"submission_artifact:group:{entity.submission_group_id}")

        if entity.submitting_member_id:
            tags.add(f"course_member:{entity.submitting_member_id}")
            tags.add(f"submission_artifact:member:{entity.submitting_member_id}")

        if entity.submit is not None:
            tags.add(f"submission_artifact:submit:{entity.submit}")

        return tags

    def get_list_tags(self, **filters) -> Set[str]:
        """Get cache tags for list queries."""
        tags = {"submission_artifact:list"}

        if "submission_group_id" in filters:
            tags.add(f"submission_artifact:group:{filters['submission_group_id']}")
            tags.add(f"submission_group:{filters['submission_group_id']}")

        if "submitting_member_id" in filters:
            tags.add(f"submission_artifact:member:{filters['submitting_member_id']}")
            tags.add(f"course_member:{filters['submitting_member_id']}")

        if "submit" in filters:
            tags.add(f"submission_artifact:submit:{filters['submit']}")

        return tags

    # ========================================================================
    # Specialized queries (with caching if enabled)
    # ========================================================================

    def find_by_submission_group(self, submission_group_id: str) -> List[SubmissionArtifact]:
        """
        Find all artifacts in a submission group (cached if enabled).

        Args:
            submission_group_id: Submission group identifier

        Returns:
            List of artifacts in the group
        """
        return self.find_by(submission_group_id=submission_group_id)

    def find_by_member(self, submitting_member_id: str) -> List[SubmissionArtifact]:
        """
        Find all artifacts submitted by a course member (cached if enabled).

        Args:
            submitting_member_id: Course member identifier

        Returns:
            List of artifacts submitted by the member
        """
        return self.find_by(submitting_member_id=submitting_member_id)

    def find_official_submissions(self, submission_group_id: str) -> List[SubmissionArtifact]:
        """
        Find all official submissions (submit=True) for a group (cached if enabled).

        Args:
            submission_group_id: Submission group identifier

        Returns:
            List of official submissions
        """
        return self.find_by(submission_group_id=submission_group_id, submit=True)

    def find_latest_by_group(self, submission_group_id: str) -> Optional[SubmissionArtifact]:
        """
        Find the latest artifact in a submission group (cached if enabled).

        Args:
            submission_group_id: Submission group identifier

        Returns:
            Latest artifact or None
        """
        # Try cache if enabled
        if self._use_cache():
            key = self.cache.key(self.entity_type, f"latest:{submission_group_id}")
            cached = self.cache.get_by_key(key)
            if cached is not None:
                return self._deserialize_entity(cached)

        # Query DB
        entity = self.db.query(SubmissionArtifact).filter(
            SubmissionArtifact.submission_group_id == submission_group_id
        ).order_by(
            SubmissionArtifact.created_at.desc()
        ).first()

        # Cache if found and caching enabled
        if entity and self._use_cache():
            key = self.cache.key(self.entity_type, f"latest:{submission_group_id}")
            tags = self.get_entity_tags(entity)
            tags.add(f"submission_artifact:latest:{submission_group_id}")
            self.cache.set_with_tags(
                key=key,
                payload=self._serialize_entity(entity),
                tags=tags,
                ttl=self.get_ttl()
            )

        return entity

    def find_active_artifacts(self) -> List[SubmissionArtifact]:
        """
        Find all non-archived artifacts (cached if enabled).

        Returns:
            List of active artifacts
        """
        return self.find_by(archived_at=None)
