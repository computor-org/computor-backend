"""Backend StudentProfile interface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.student_profile import (
    StudentProfileInterface as StudentProfileInterfaceBase,
    StudentProfileQuery,
)
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.auth import StudentProfile


class StudentProfileInterface(StudentProfileInterfaceBase, BackendEntityInterface):
    """Backend-specific StudentProfile interface with model attached."""

    model = StudentProfile
    endpoint = "student-profiles"
    cache_ttl = 300

    @staticmethod
    def search(db: Session, query, params: Optional[StudentProfileQuery]):
        """
        Apply search filters to studentprofile query.
        
        Note: Implement specific filters based on query parameters.
        This is a placeholder - update with actual filter logic.
        """
        # TODO: Implement search filters based on StudentProfileQuery fields
        return query
