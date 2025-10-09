"""Backend student courses interface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.student_courses import (
    CourseStudentInterface as CourseStudentInterfaceBase,
    CourseStudentQuery,
)
from computor_types.custom_types import Ltree
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.course import Course


class CourseStudentInterface(CourseStudentInterfaceBase, BackendEntityInterface):
    """Backend-specific student course interface with model attached."""

    model = Course
    endpoint = "courses"
    cache_ttl = 300

    @staticmethod
    def search(db: Session, query, params: Optional[CourseStudentQuery]):
        """Apply search filters to student course query."""
        if params is None:
            return query

        if params.id is not None:
            query = query.filter(Course.id == params.id)
        if params.title is not None:
            query = query.filter(Course.title == params.title)
        if params.description is not None:
            query = query.filter(Course.description.ilike(f"%{params.description}%"))
        if params.path is not None:
            query = query.filter(Course.path == Ltree(params.path))
        if params.course_family_id is not None:
            query = query.filter(Course.course_family_id == params.course_family_id)
        if params.organization_id is not None:
            query = query.filter(Course.organization_id == params.organization_id)

        # GitLab-specific filters
        if params.provider_url is not None:
            query = query.filter(Course.properties["gitlab"].op("->>")("url") == params.provider_url)
        if params.full_path is not None:
            query = query.filter(Course.properties["gitlab"].op("->>")("full_path") == params.full_path)
        if params.full_path_student is not None:
            from computor_backend.model.course import CourseMember
            query = query.join(CourseMember, CourseMember.course_id == Course.id).filter(
                CourseMember.properties["gitlab"].op("->>")("full_path") == params.full_path_student
            )

        return query
