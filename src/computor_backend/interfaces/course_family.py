"""Backend CourseFamily interface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.course_families import (
    CourseFamilyInterface as CourseFamilyInterfaceBase,
    CourseFamilyQuery,
)
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.course import CourseFamily


class CourseFamilyInterface(CourseFamilyInterfaceBase, BackendEntityInterface):
    """Backend-specific CourseFamily interface with model attached."""

    model = CourseFamily
    endpoint = "course-families"
    cache_ttl = 600

    @staticmethod
    def search(db: Session, query, params: Optional[CourseFamilyQuery]):
        """Apply search filters to course family query."""
        if params.id is not None:
            query = query.filter(CourseFamily.id == params.id)
        if params.title is not None:
            query = query.filter(CourseFamily.title == params.title)
        if params.abbreviation is not None:
            query = query.filter(CourseFamily.abbreviation == params.abbreviation)
        if params.organization_id is not None:
            query = query.filter(CourseFamily.organization_id == params.organization_id)
        if params.archived is not None and params.archived:
            query = query.filter(CourseFamily.archived_at.isnot(None))
        else:
            query = query.filter(CourseFamily.archived_at.is_(None))

        return query
