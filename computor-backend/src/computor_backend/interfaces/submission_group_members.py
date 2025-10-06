"""Backend SubmissionGroupMemberInterface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.submission_group_members import SubmissionGroupMemberInterface as SubmissionGroupMemberInterfaceBase, SubmissionGroupMemberQuery
from computor_backend.interfaces.base import BackendEntityInterface
# TODO: Import actual model when available
# from computor_backend.model import SubmissionGroupMember

class SubmissionGroupMemberInterface(SubmissionGroupMemberInterfaceBase, BackendEntityInterface):
    """Backend-specific SubmissionGroupMemberInterface with model and API configuration."""
    
    # model = SubmissionGroupMember  # TODO: Set when model is available
    endpoint = "submission-group-members"
    cache_ttl = 600

    @staticmethod
    def search(db: Session, query, params: Optional[SubmissionGroupMemberQuery]):
        """
        Apply search filters to submissiongroupmember query.
        
        Args:
            db: Database session
            query: SQLAlchemy query object
            params: Query parameters
            
        Returns:
            Filtered query object
        """
        # TODO: Implement search logic when model is available
        return query
