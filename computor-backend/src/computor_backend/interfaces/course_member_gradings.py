"""Backend CourseMemberGradings interface.

This is a read-only interface that provides aggregated progress statistics
for course members. It does not have a SQLAlchemy model since it performs
aggregation queries across multiple tables.
"""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.course_member_gradings import (
    CourseMemberGradingsInterface as CourseMemberGradingsInterfaceBase,
    CourseMemberGradingsQuery,
)
from computor_backend.interfaces.base import BackendEntityInterface


class CourseMemberGradingsInterface(CourseMemberGradingsInterfaceBase, BackendEntityInterface):
    """Backend-specific CourseMemberGradings interface.

    This is a read-only aggregation interface without a direct SQLAlchemy model.
    The endpoint calculates statistics by joining course_content, submission_artifact,
    and related tables.
    """

    # No model - this is an aggregation endpoint
    model = None
    endpoint = "course-member-gradings"
    cache_ttl = 60  # Cache for 1 minute since it's an expensive query

    @staticmethod
    def search(db: Session, query, params: Optional[CourseMemberGradingsQuery]):
        """
        Apply search filters to course member gradings query.

        Note: This interface doesn't use the standard CRUD pattern,
        so this search function is provided for interface compatibility
        but actual filtering is done in the business logic layer.

        Args:
            db: Database session
            query: SQLAlchemy query object
            params: Query parameters

        Returns:
            Filtered query object (passthrough for this interface)
        """
        # Filtering is handled in business logic since this is an aggregation endpoint
        return query
