"""Backend CourseExecutionBackend interface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.course_execution_backends import (
    CourseExecutionBackendInterface as CourseExecutionBackendInterfaceBase,
    CourseExecutionBackendQuery,
)
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.course import CourseExecutionBackend


class CourseExecutionBackendInterface(CourseExecutionBackendInterfaceBase, BackendEntityInterface):
    """Backend-specific CourseExecutionBackend interface with model attached."""

    model = CourseExecutionBackend
    endpoint = "course-execution-backends"
    cache_ttl = 300

    @staticmethod
    def search(db: Session, query, params: Optional[CourseExecutionBackendQuery]):
        """Apply search filters to course execution backend query."""
        if params is None:
            return query

        if params.execution_backend_id is not None:
            query = query.filter(CourseExecutionBackend.execution_backend_id == params.execution_backend_id)
        if params.course_id is not None:
            query = query.filter(CourseExecutionBackend.course_id == params.course_id)

        return query
