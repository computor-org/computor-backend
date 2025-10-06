"""Backend CourseContentKindInterface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.course_content_kind import CourseContentKindInterface as CourseContentKindInterfaceBase, CourseContentKindQuery
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.course import CourseContentKind

class CourseContentKindInterface(CourseContentKindInterfaceBase, BackendEntityInterface):
    """Backend-specific CourseContentKindInterface with model and API configuration."""
    
    model = CourseContentKind
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
        
        if params is None:
            return query

        if params.id is not None:
            query = query.filter(CourseContentKind.id == params.id)
        if params.title is not None:
            query = query.filter(CourseContentKind.title == params.title)
        if params.description is not None:
            query = query.filter(CourseContentKind.description.ilike(f"%{params.description}%"))
        if params.has_ascendants is not None:
            query = query.filter(CourseContentKind.has_ascendants == params.has_ascendants)
        if params.has_descendants is not None:
            query = query.filter(CourseContentKind.has_descendants == params.has_descendants)
        if params.submittable is not None:
            query = query.filter(CourseContentKind.submittable == params.submittable)

        return query
