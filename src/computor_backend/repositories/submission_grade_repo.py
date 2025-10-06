"""
SubmissionGrade repository for database access with cache invalidation.

This module provides the SubmissionGradeRepository class that handles
all database operations for SubmissionGrade entities with automatic cache invalidation.
"""

from typing import List, Optional, Set
from uuid import UUID
from sqlalchemy.orm import Session

from .base import BaseRepository
from ..model.artifact import SubmissionGrade


class SubmissionGradeRepository(BaseRepository[SubmissionGrade]):
    """
    Repository for SubmissionGrade entity with automatic cache invalidation.

    Handles submission grading CRUD operations and ensures all related caches
    (artifact views, student views, grading views) are properly invalidated.
    """

    def __init__(self, db: Session, cache=None):
        """
        Initialize submission grade repository.

        Args:
            db: SQLAlchemy session
            cache: Optional Cache instance (enables transparent caching)
        """
        super().__init__(db, SubmissionGrade, cache)

    # ========================================================================
    # Cache configuration
    # ========================================================================

    @property
    def entity_type(self) -> str:
        """Entity type identifier for cache keys."""
        return "submission_grade"

    def get_ttl(self) -> int:
        """Grades change moderately - use 5 minute TTL."""
        return 300  # 5 minutes

    def get_entity_tags(self, entity: SubmissionGrade) -> Set[str]:
        """
        Get cache tags for submission grade.

        Tags:
        - submission_grade:{id} - The specific grade
        - submission_grade:list - All grade list queries
        - submission_artifact:{artifact_id} - Invalidate artifact-level caches
        - submission_grade:artifact:{artifact_id} - Grades for this artifact
        - submission_grade:grader:{grader_id} - Grades by this grader
        """
        tags = {
            f"submission_grade:{entity.id}",
            "submission_grade:list",
        }

        if entity.artifact_id:
            tags.add(f"submission_grade:artifact:{entity.artifact_id}")
            tags.add(f"submission_artifact:{entity.artifact_id}")

        if entity.graded_by_course_member_id:
            tags.add(f"submission_grade:grader:{entity.graded_by_course_member_id}")

        # Status-based tags for filtering
        if entity.status is not None:
            tags.add(f"submission_grade:status:{entity.status}")

        return tags

    def get_list_tags(self, **filters) -> Set[str]:
        """Get cache tags for list queries."""
        tags = {"submission_grade:list"}

        if "artifact_id" in filters:
            tags.add(f"submission_grade:artifact:{filters['artifact_id']}")
            tags.add(f"submission_artifact:{filters['artifact_id']}")

        if "graded_by_course_member_id" in filters:
            tags.add(f"submission_grade:grader:{filters['graded_by_course_member_id']}")

        if "status" in filters:
            tags.add(f"submission_grade:status:{filters['status']}")

        return tags

    # ========================================================================
    # Specialized queries
    # ========================================================================

    def find_by_artifact(self, artifact_id: str | UUID) -> List[SubmissionGrade]:
        """
        Find all grades for a submission artifact.

        Args:
            artifact_id: Submission artifact identifier

        Returns:
            List of grades ordered by graded_at descending
        """
        query = self.db.query(SubmissionGrade).filter(
            SubmissionGrade.artifact_id == str(artifact_id)
        ).order_by(SubmissionGrade.graded_at.desc())

        return query.all()

    def find_by_grader(self, grader_id: str | UUID) -> List[SubmissionGrade]:
        """
        Find all grades given by a specific grader.

        Args:
            grader_id: Course member identifier of the grader

        Returns:
            List of grades ordered by graded_at descending
        """
        query = self.db.query(SubmissionGrade).filter(
            SubmissionGrade.graded_by_course_member_id == str(grader_id)
        ).order_by(SubmissionGrade.graded_at.desc())

        return query.all()

    def find_latest_by_artifact(self, artifact_id: str | UUID) -> Optional[SubmissionGrade]:
        """
        Find the most recent grade for a submission artifact.

        Args:
            artifact_id: Submission artifact identifier

        Returns:
            Latest SubmissionGrade if exists, None otherwise
        """
        return self.db.query(SubmissionGrade).filter(
            SubmissionGrade.artifact_id == str(artifact_id)
        ).order_by(SubmissionGrade.graded_at.desc()).first()

    def find_by_status(self, status: int) -> List[SubmissionGrade]:
        """
        Find all grades with a specific status.

        Args:
            status: Grading status (0=not_reviewed, 1=corrected, 2=correction_necessary, 3=improvement_possible)

        Returns:
            List of grades with this status
        """
        return self.find_by(status=status)

    def get_average_grade_for_artifact(self, artifact_id: str | UUID) -> Optional[float]:
        """
        Calculate average grade for an artifact.

        Args:
            artifact_id: Submission artifact identifier

        Returns:
            Average grade as float, None if no grades exist
        """
        from sqlalchemy import func

        result = self.db.query(
            func.avg(SubmissionGrade.grade)
        ).filter(
            SubmissionGrade.artifact_id == str(artifact_id)
        ).scalar()

        return float(result) if result is not None else None
