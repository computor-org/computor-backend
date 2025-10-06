"""Backend SubmissionGroupInterface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.submission_groups import SubmissionGroupInterface as SubmissionGroupInterfaceBase, SubmissionGroupQuery
from computor_backend.interfaces.base import BackendEntityInterface
# TODO: Import actual model when available
# from computor_backend.model import SubmissionGroup

class SubmissionGroupInterface(SubmissionGroupInterfaceBase, BackendEntityInterface):
    """Backend-specific SubmissionGroupInterface with model and API configuration."""
    
    # model = SubmissionGroup  # TODO: Set when model is available
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
        # TODO: Implement search logic when model is available
        return query
