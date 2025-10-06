"""Backend CourseContent interface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.course_contents import (
    CourseContentInterface as CourseContentInterfaceBase,
    CourseContentQuery,
)
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.course import CourseContent


class CourseContentInterface(CourseContentInterfaceBase, BackendEntityInterface):
    """Backend-specific CourseContent interface with model attached."""

    model = CourseContent
    endpoint = "course-contents"
    cache_ttl = 300

    @staticmethod
    def search(db: Session, query, params: Optional[CourseContentQuery]):
        """
        Apply search filters to coursecontent query.

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
            query = query.filter(CourseContent.id == params.id)
        if params.title is not None:
            query = query.filter(CourseContent.title == params.title)
        if params.description is not None:
            query = query.filter(CourseContent.description.ilike(f"%{params.description}%"))
        if params.path is not None:
            query = query.filter(CourseContent.path == params.path)
        if params.course_id is not None:
            query = query.filter(CourseContent.course_id == params.course_id)
        if params.course_content_type_id is not None:
            query = query.filter(CourseContent.course_content_type_id == params.course_content_type_id)
        if params.execution_backend_id is not None:
            query = query.filter(CourseContent.execution_backend_id == params.execution_backend_id)
        if params.example_version_id is not None:
            query = query.filter(CourseContent.example_version_id == params.example_version_id)

        return query
