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
        """Apply search filters to student profile query."""
        if params is None:
            return query

        if params.id is not None:
            query = query.filter(StudentProfile.id == params.id)
        if params.student_id is not None:
            query = query.filter(StudentProfile.student_id == params.student_id)
        if params.student_email is not None:
            query = query.filter(StudentProfile.student_email == params.student_email)
        if params.user_id is not None:
            query = query.filter(StudentProfile.user_id == params.user_id)
        if params.organization_id is not None:
            query = query.filter(StudentProfile.organization_id == params.organization_id)

        return query
