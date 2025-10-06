"""Backend Course interface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.courses import (
    CourseInterface as CourseInterfaceBase,
    CourseQuery,
)
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.course import Course


class CourseInterface(CourseInterfaceBase, BackendEntityInterface):
    """Backend-specific Course interface with model attached."""

    model = Course
    endpoint = "courses"
    cache_ttl = 300

    @staticmethod
    def search(db: Session, query, params: Optional[CourseQuery]):
        """Apply search filters to course query."""
        if params.id is not None:
            query = query.filter(Course.id == params.id)
        if params.title is not None:
            query = query.filter(Course.title == params.title)
        if params.abbreviation is not None:
            query = query.filter(Course.abbreviation == params.abbreviation)
        if params.course_family_id is not None:
            query = query.filter(Course.course_family_id == params.course_family_id)
        if params.archived is not None and params.archived:
            query = query.filter(Course.archived_at.isnot(None))
        else:
            query = query.filter(Course.archived_at.is_(None))

        return query
