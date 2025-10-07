"""Backend Course interface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.courses import (
    CourseInterface as CourseInterfaceBase,
    CourseQuery,
)
from computor_types.custom_types import Ltree
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
        if params is None:
            return query

        if params.id is not None:
            query = query.filter(Course.id == params.id)
        if params.title is not None:
            query = query.filter(Course.title == params.title)
        if params.description is not None:
            query = query.filter(Course.description.ilike(f"%{params.description}%"))
        if params.path is not None:
            # Convert string to Ltree for proper comparison
            query = query.filter(Course.path == Ltree(params.path))
        if params.course_family_id is not None:
            query = query.filter(Course.course_family_id == params.course_family_id)
        if params.organization_id is not None:
            query = query.filter(Course.organization_id == params.organization_id)
        if params.language_code is not None:
            query = query.filter(Course.language_code == params.language_code)

        return query
