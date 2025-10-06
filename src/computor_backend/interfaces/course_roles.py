"""Backend CourseRoleInterface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.course_roles import CourseRoleInterface as CourseRoleInterfaceBase, CourseRoleQuery
from computor_backend.interfaces.base import BackendEntityInterface
# TODO: Import actual model when available
# from computor_backend.model import CourseRole

class CourseRoleInterface(CourseRoleInterfaceBase, BackendEntityInterface):
    """Backend-specific CourseRoleInterface with model and API configuration."""
    
    # model = CourseRole  # TODO: Set when model is available
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
        # TODO: Implement search logic when model is available
        return query
