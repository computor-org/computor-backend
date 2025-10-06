"""Backend CourseContentKindInterface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.course_content_kind import CourseContentKindInterface as CourseContentKindInterfaceBase, CourseContentKindQuery
from computor_backend.interfaces.base import BackendEntityInterface
# TODO: Import actual model when available
# from computor_backend.model import CourseContentKind

class CourseContentKindInterface(CourseContentKindInterfaceBase, BackendEntityInterface):
    """Backend-specific CourseContentKindInterface with model and API configuration."""
    
    # model = CourseContentKind  # TODO: Set when model is available
    endpoint = "course-content-kind"
    cache_ttl = 600

    @staticmethod
    def search(db: Session, query, params: Optional[CourseContentKindQuery]):
        """
        Apply search filters to coursecontentkind query.
        
        Args:
            db: Database session
            query: SQLAlchemy query object
            params: Query parameters
            
        Returns:
            Filtered query object
        """
        # TODO: Implement search logic when model is available
        return query
