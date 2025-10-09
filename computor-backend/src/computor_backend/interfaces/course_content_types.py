"""Backend CourseContentTypeInterface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.course_content_types import CourseContentTypeInterface as CourseContentTypeInterfaceBase, CourseContentTypeQuery
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.course import CourseContentType

class CourseContentTypeInterface(CourseContentTypeInterfaceBase, BackendEntityInterface):
    """Backend-specific CourseContentTypeInterface with model and API configuration."""

    model = CourseContentType
    endpoint = "course-content-types"
    cache_ttl = 600

    @staticmethod
    def search(db: Session, query, params: Optional[CourseContentTypeQuery]):
        """
        Apply search filters to coursecontenttype query.

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
            query = query.filter(CourseContentType.id == params.id)
        if params.slug is not None:
            query = query.filter(CourseContentType.slug == params.slug)
        if params.title is not None:
            query = query.filter(CourseContentType.title == params.title)
        if params.color is not None:
            query = query.filter(CourseContentType.color == params.color)
        if params.description is not None:
            query = query.filter(CourseContentType.description == params.description)
        if params.course_id is not None:
            query = query.filter(CourseContentType.course_id == params.course_id)
        if params.course_content_kind_id is not None:
            query = query.filter(CourseContentType.course_content_kind_id == params.course_content_kind_id)

        return query
