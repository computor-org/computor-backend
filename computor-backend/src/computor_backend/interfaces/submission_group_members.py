"""Backend SubmissionGroupMemberInterface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.submission_group_members import SubmissionGroupMemberInterface as SubmissionGroupMemberInterfaceBase, SubmissionGroupMemberQuery
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.course import SubmissionGroupMember

class SubmissionGroupMemberInterface(SubmissionGroupMemberInterfaceBase, BackendEntityInterface):
    """Backend-specific SubmissionGroupMemberInterface with model and API configuration."""
    
    model = SubmissionGroupMember
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
        
        if params is None:
            return query

        if params.id is not None:
            query = query.filter(SubmissionGroupMember.id == params.id)
        if params.submission_group_id is not None:
            query = query.filter(SubmissionGroupMember.submission_group_id == params.submission_group_id)
        if params.course_member_id is not None:
            query = query.filter(SubmissionGroupMember.course_member_id == params.course_member_id)

        return query
