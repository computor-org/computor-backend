"""Backend CourseMember interface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.course_members import (
    CourseMemberInterface as CourseMemberInterfaceBase,
    CourseMemberQuery,
)
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.course import CourseMember


class CourseMemberInterface(CourseMemberInterfaceBase, BackendEntityInterface):
    """Backend-specific CourseMember interface with model attached."""

    model = CourseMember
    endpoint = "course-members"
    cache_ttl = 300

    @staticmethod
    def search(db: Session, query, params: Optional[CourseMemberQuery]):
        """
        Apply search filters to coursemember query.
        
        Note: Implement specific filters based on query parameters.
        This is a placeholder - update with actual filter logic.
        """
        # TODO: Implement search filters based on CourseMemberQuery fields
        return query
