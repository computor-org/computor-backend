"""Backend Student Course Content interface with search method."""

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from computor_types.student_course_contents import (
    CourseContentStudentInterface as CourseContentStudentInterfaceBase,
    CourseContentStudentQuery,
)
from computor_backend.business_logic.content_visibility import (
    student_visible_predicate,
)
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.course import CourseContent
from computor_types.custom_types import Ltree


class CourseContentStudentInterface(CourseContentStudentInterfaceBase, BackendEntityInterface):
    """Backend-specific Student Course Content interface."""

    model = CourseContent
    endpoint = "students/course-contents"
    cache_ttl = 300

    @staticmethod
    def search(
        db: Session,
        query,
        params: Optional[CourseContentStudentQuery],
        *,
        include_hidden: bool = False,
    ):
        """Apply search filters to course content query for students.

        ``include_hidden`` is what separates a student from a staff member
        looking at the same view. This one function serves both the student's
        own tree and a tutor's view of a student (issue #338), and only the
        former may lose rows -- so the caller decides rather than this function
        guessing. It defaults to False so a caller that forgets errs on the
        side of hiding.

        It governs both reasons a row is dropped: hidden by a lecturer (#338)
        and never released (#163). Staff see everything either way.
        """
        # Students never see archived content
        query = query.filter(CourseContent.archived_at.is_(None))

        # ...nor content hidden by their lecturer, here or on any ancestor,
        # nor an assignment that has never been released to them (#163).
        # Filtered in SQL rather than after the fact so the row never reaches
        # a student's payload at all.
        if not include_hidden:
            query = query.filter(student_visible_predicate())

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
