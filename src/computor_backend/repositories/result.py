"""
Result repository for direct database access with optional caching.

This module provides the ResultRepository class that handles
all database operations for Result entities with transparent caching.

CRITICAL: This repository invalidates tutor/lecturer/student view caches
when results change, ensuring views reflect current test results.
"""

from typing import List, Optional, Set
from sqlalchemy.orm import Session

from .base import BaseRepository
from ..model.result import Result
from ..model.course import CourseContent


class ResultRepository(BaseRepository[Result]):
    """
    Repository for Result entity database operations with optional caching.

    Caching is automatic when cache instance is provided to constructor.
    """

    def __init__(self, db: Session, cache=None):
        """
        Initialize result repository.

        Args:
            db: SQLAlchemy session
            cache: Optional Cache instance (enables transparent caching)
        """
        super().__init__(db, Result, cache)

    # ========================================================================
    # Cache configuration
    # ========================================================================

    @property
    def entity_type(self) -> str:
        """Entity type identifier for cache keys."""
        return "result"

    def get_ttl(self) -> int:
        """Results are frequently created during testing - use 5 minute TTL."""
        return 300  # 5 minutes

    def _get_course_id_from_result(self, entity: Result) -> Optional[str]:
        """
        Get the course_id for a result by querying course_content.

        This is needed to invalidate tutor/lecturer/student view caches.
        """
        if not entity.course_content_id:
            return None

        # Query course_content to get course_id
        course_content = self.db.query(CourseContent).filter(
            CourseContent.id == entity.course_content_id
        ).first()

        return str(course_content.course_id) if course_content else None

    def get_entity_tags(self, entity: Result) -> Set[str]:
        """
        Get cache tags for a result.

        Tags:
        - result:{id} - The specific result
        - result:list - All result listings
        - submission_artifact:{artifact_id} - All results for this artifact
        - result:artifact:{artifact_id} - Artifact-specific results
        - submission_group:{group_id} - All results for this group
        - result:group:{group_id} - Group-specific results
        - course_content:{content_id} - All results for this content
        - result:content:{content_id} - Content-specific results
        - result:status:{status} - Results with specific status
        - tutor_view:{course_id} - Tutor views for this course (CRITICAL)
        - lecturer_view:{course_id} - Lecturer views for this course (CRITICAL)
        - student_view:{course_id} - Student views for this course
        """
        tags = {
            f"result:{entity.id}",
            "result:list",
        }

        if entity.submission_artifact_id:
            tags.add(f"submission_artifact:{entity.submission_artifact_id}")
            tags.add(f"result:artifact:{entity.submission_artifact_id}")

        if entity.submission_group_id:
            tags.add(f"submission_group:{entity.submission_group_id}")
            tags.add(f"result:group:{entity.submission_group_id}")

        if entity.course_content_id:
            tags.add(f"course_content:{entity.course_content_id}")
            tags.add(f"result:content:{entity.course_content_id}")

            # CRITICAL: Invalidate tutor/lecturer/student views when result changes
            # Get course_id to invalidate view caches
            course_id = self._get_course_id_from_result(entity)
            if course_id:
                tags.add(f"tutor_view:{course_id}")      # Tutors see results
                tags.add(f"lecturer_view:{course_id}")   # Lecturers see results
                tags.add(f"student_view:{course_id}")    # Students see their own results

        if entity.status is not None:
            tags.add(f"result:status:{entity.status}")

        return tags

    def get_list_tags(self, **filters) -> Set[str]:
        """Get cache tags for list queries."""
        tags = {"result:list"}

        if "submission_artifact_id" in filters:
            tags.add(f"result:artifact:{filters['submission_artifact_id']}")
            tags.add(f"submission_artifact:{filters['submission_artifact_id']}")

        if "submission_group_id" in filters:
            tags.add(f"result:group:{filters['submission_group_id']}")
            tags.add(f"submission_group:{filters['submission_group_id']}")

        if "course_content_id" in filters:
            tags.add(f"result:content:{filters['course_content_id']}")
            tags.add(f"course_content:{filters['course_content_id']}")

        if "status" in filters:
            tags.add(f"result:status:{filters['status']}")

        return tags

    # ========================================================================
    # Specialized queries (with caching if enabled)
    # ========================================================================

    def find_by_artifact(self, submission_artifact_id: str) -> List[Result]:
        """
        Find all results for a submission artifact (cached if enabled).

        Args:
            submission_artifact_id: Submission artifact identifier

        Returns:
            List of results for the artifact
        """
        return self.find_by(submission_artifact_id=submission_artifact_id)

    def find_by_submission_group(self, submission_group_id: str) -> List[Result]:
        """
        Find all results for a submission group (cached if enabled).

        Args:
            submission_group_id: Submission group identifier

        Returns:
            List of results for the group
        """
        return self.find_by(submission_group_id=submission_group_id)

    def find_by_course_content(self, course_content_id: str) -> List[Result]:
        """
        Find all results for a course content (cached if enabled).

        Args:
            course_content_id: Course content identifier

        Returns:
            List of results for the content
        """
        return self.find_by(course_content_id=course_content_id)

    def find_by_status(self, status: int) -> List[Result]:
        """
        Find all results with a specific status (cached if enabled).

        Args:
            status: Result status (0=FINISHED, etc.)

        Returns:
            List of results with the status
        """
        return self.find_by(status=status)

    def find_finished_results(self) -> List[Result]:
        """
        Find all finished results (status=0) (cached if enabled).

        Returns:
            List of finished results
        """
        return self.find_by(status=0)

    def find_latest_by_artifact(self, submission_artifact_id: str) -> Optional[Result]:
        """
        Find the latest result for an artifact (cached if enabled).

        Args:
            submission_artifact_id: Submission artifact identifier

        Returns:
            Latest result or None
        """
        # Try cache if enabled
        if self._use_cache():
            key = self.cache.key(self.entity_type, f"latest:{submission_artifact_id}")
            cached = self.cache.get_by_key(key)
            if cached is not None:
                return self._deserialize_entity(cached)

        # Query DB
        entity = self.db.query(Result).filter(
            Result.submission_artifact_id == submission_artifact_id
        ).order_by(
            Result.created_at.desc()
        ).first()

        # Cache if found and caching enabled
        if entity and self._use_cache():
            key = self.cache.key(self.entity_type, f"latest:{submission_artifact_id}")
            tags = self.get_entity_tags(entity)
            tags.add(f"result:latest:{submission_artifact_id}")
            self.cache.set_with_tags(
                key=key,
                payload=self._serialize_entity(entity),
                tags=tags,
                ttl=self.get_ttl()
            )

        return entity
