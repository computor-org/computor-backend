"""Backend CourseGroupInterface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.course_groups import CourseGroupInterface as CourseGroupInterfaceBase, CourseGroupQuery
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.course import CourseGroup

class CourseGroupInterface(CourseGroupInterfaceBase, BackendEntityInterface):
    """Backend-specific CourseGroupInterface with model and API configuration."""
    
    model = CourseGroup
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
        
        if params is None:
            return query

        if params.id is not None:
            query = query.filter(CourseGroup.id == params.id)
        if params.title is not None:
            query = query.filter(CourseGroup.title == params.title)
        if params.course_id is not None:
            query = query.filter(CourseGroup.course_id == params.course_id)

        return query
