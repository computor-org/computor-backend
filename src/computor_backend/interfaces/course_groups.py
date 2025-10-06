"""Backend CourseGroupInterface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.course_groups import CourseGroupInterface as CourseGroupInterfaceBase, CourseGroupQuery
from computor_backend.interfaces.base import BackendEntityInterface
# TODO: Import actual model when available
# from computor_backend.model import CourseGroup

class CourseGroupInterface(CourseGroupInterfaceBase, BackendEntityInterface):
    """Backend-specific CourseGroupInterface with model and API configuration."""
    
    # model = CourseGroup  # TODO: Set when model is available
    endpoint = "course-groups"
    cache_ttl = 600

    @staticmethod
    def search(db: Session, query, params: Optional[CourseGroupQuery]):
        """
        Apply search filters to coursegroup query.
        
        Args:
            db: Database session
            query: SQLAlchemy query object
            params: Query parameters
            
        Returns:
            Filtered query object
        """
        # TODO: Implement search logic when model is available
        return query
