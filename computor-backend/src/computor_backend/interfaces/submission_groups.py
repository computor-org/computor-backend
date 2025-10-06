"""Backend SubmissionGroupInterface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.submission_groups import SubmissionGroupInterface as SubmissionGroupInterfaceBase, SubmissionGroupQuery
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.course import SubmissionGroup

class SubmissionGroupInterface(SubmissionGroupInterfaceBase, BackendEntityInterface):
    """Backend-specific SubmissionGroupInterface with model and API configuration."""
    
    model = SubmissionGroup
    endpoint = "submission-groups"
    cache_ttl = 600

    @staticmethod
    def search(db: Session, query, params: Optional[SubmissionGroupQuery]):
        """
        Apply search filters to submissiongroup query.
        
        Args:
            db: Database session
            query: SQLAlchemy query object
            params: Query parameters
            
        Returns:
            Filtered query object
        """
        
        if params is None:
            return query

        if params.id is not None:
            query = query.filter(SubmissionGroup.id == params.id)
        if params.course_content_id is not None:
            query = query.filter(SubmissionGroup.course_content_id == params.course_content_id)

        return query
