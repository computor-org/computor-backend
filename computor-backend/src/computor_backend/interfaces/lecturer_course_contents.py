"""Backend Lecturer Course Content interface with search method."""

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from computor_types.lecturer_course_contents import (
    CourseContentLecturerInterface as CourseContentLecturerInterfaceBase,
    CourseContentLecturerQuery,
)
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.course import CourseContent
from computor_types.custom_types import Ltree


class CourseContentLecturerInterface(CourseContentLecturerInterfaceBase, BackendEntityInterface):
    """Backend-specific Lecturer Course Content interface."""

    model = CourseContent
    endpoint = "lecturers/course-contents"
    cache_ttl = 300

    @staticmethod
    def search(db: Session, query, params: Optional[CourseContentLecturerQuery]):
        """Apply search filters to course content query for lecturers."""
        if params is None:
            return query

        if params.id is not None:
            query = query.filter(CourseContent.id == params.id)
        if params.title is not None:
            query = query.filter(CourseContent.title == params.title)
        if params.path is not None:
            query = query.filter(CourseContent.path == Ltree(params.path))
        if params.course_id is not None:
            query = query.filter(CourseContent.course_id == params.course_id)
        if params.course_content_type_id is not None:
            query = query.filter(CourseContent.course_content_type_id == params.course_content_type_id)

        # GitLab-specific filters (only for GitLab courses)
        if params.directory is not None:
            query = query.filter(CourseContent.properties["gitlab"].op("->>")("directory") == params.directory)
        if params.project is not None:
            query = query.filter(CourseContent.properties["gitlab"].op("->>")("full_path") == params.project)
        if params.provider_url is not None:
            query = query.filter(CourseContent.properties["gitlab"].op("->>")("url") == params.provider_url)

        # Ltree hierarchy filters
        if params.nlevel is not None:
            query = query.filter(func.nlevel(CourseContent.path) == params.nlevel)
        if params.descendants is not None:
            query = query.filter(
                and_(
                    CourseContent.path.descendant_of(Ltree(params.descendants)),
                    CourseContent.path != Ltree(params.descendants)
                )
            )
        if params.ascendants is not None:
            query = query.filter(
                and_(
                    CourseContent.path.ancestor_of(Ltree(params.ascendants)),
                    CourseContent.path != Ltree(params.ascendants)
                )
            )

        # Order by position
        query = query.order_by(CourseContent.position)

        return query
