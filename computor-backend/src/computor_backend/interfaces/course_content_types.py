"""Backend CourseContentTypeInterface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.course_content_types import CourseContentTypeInterface as CourseContentTypeInterfaceBase, CourseContentTypeQuery
from computor_backend.interfaces.base import BackendEntityInterface
# TODO: Import actual model when available
# from computor_backend.model import CourseContentType

class CourseContentTypeInterface(CourseContentTypeInterfaceBase, BackendEntityInterface):
    """Backend-specific CourseContentTypeInterface with model and API configuration."""
    
    # model = CourseContentType  # TODO: Set when model is available
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
        # TODO: Implement search logic when model is available
        return query
