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
            query = query.filter(CourseMember.id == params.id)
        if params.user_id is not None:
            query = query.filter(CourseMember.user_id == params.user_id)
        if params.course_id is not None:
            query = query.filter(CourseMember.course_id == params.course_id)
        if params.course_group_id is not None:
            query = query.filter(CourseMember.course_group_id == params.course_group_id)
        if params.course_role_id is not None:
            query = query.filter(CourseMember.course_role_id == params.course_role_id)

        return query
