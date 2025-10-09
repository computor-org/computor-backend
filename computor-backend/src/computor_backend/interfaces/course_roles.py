"""Backend CourseRoleInterface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.course_roles import CourseRoleInterface as CourseRoleInterfaceBase, CourseRoleQuery
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.course import CourseRole

class CourseRoleInterface(CourseRoleInterfaceBase, BackendEntityInterface):
    """Backend-specific CourseRoleInterface with model and API configuration."""
    
    model = CourseRole
    endpoint = "course-roles"
    cache_ttl = 600

    @staticmethod
    def search(db: Session, query, params: Optional[CourseRoleQuery]):
        """
        Apply search filters to courserole query.
        
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
            query = query.filter(CourseRole.id == params.id)
        if params.title is not None:
            query = query.filter(CourseRole.title == params.title)

        return query
