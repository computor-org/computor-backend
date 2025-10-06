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
        
        Note: Implement specific filters based on query parameters.
        This is a placeholder - update with actual filter logic.
        """
        # TODO: Implement search filters based on CourseContentQuery fields
        return query
