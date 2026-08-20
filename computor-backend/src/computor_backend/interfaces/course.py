"""Backend Course interface with SQLAlchemy model."""

import logging
from typing import Optional
from sqlalchemy.orm import Session

from computor_types.courses import (
    CourseInterface as CourseInterfaceBase,
    CourseQuery,
)
from computor_types.custom_types import Ltree
from computor_backend.interfaces.base import BackendEntityInterface, CacheTag
from computor_backend.model.course import Course
from computor_backend.websocket import publish_course_updated

logger = logging.getLogger(__name__)


async def post_update_course(course, old_course, db):
    """Tell subscribed clients a course changed.

    Course settings fan out to every enrolled student -- ``visible`` hides the
    whole content tree (issue #338), and the budget defaults change what the
    tree reports. There was no course-level event at all before this, so such
    an edit only surfaced when a client's 5-minute view cache expired.
    """
    try:
        change_type = "updated"
        if getattr(old_course, "visible", None) != getattr(course, "visible", None):
            change_type = "visibility_changed"

        publish_course_updated(str(course.id), change_type)
    except Exception:
        # Never fail a committed write because a broadcast could not go out.
        logger.exception(
            "Failed to publish update event for course %s", getattr(course, "id", None)
        )


class CourseInterface(CourseInterfaceBase, BackendEntityInterface):
    """Backend-specific Course interface with model attached."""

    model = Course
    endpoint = "courses"
    cache_ttl = 300
    post_update = post_update_course

    @classmethod
    def cache_invalidation_tags(cls, entity):
        """Course's own ``id`` is the ``course_id`` other entities key on.

        The student and tutor view tags matter as much as the lecturer one:
        ``Course.visible`` hides every course content beneath it (issue #338),
        and ``max_test_runs`` / ``max_submissions`` are course-wide budget
        defaults. Without these, a course-level edit sat behind the student
        view's 300 s TTL -- exactly the failure ``CourseContentInterface``
        documents for #337, one level up.
        """
        if entity.id is None:
            return
        cid = str(entity.id)
        yield CacheTag.for_entity("course_id", cid)
        yield CacheTag.for_entity("lecturer_view", cid)
        yield CacheTag.for_entity("student_view", cid)
        yield CacheTag.for_entity("tutor_view", cid)

    @staticmethod
    def search(db: Session, query, params: Optional[CourseQuery]):
        """Apply search filters to course query."""
        if params is None:
            return query

        if params.id is not None:
            query = query.filter(Course.id == params.id)
        if params.title is not None:
            query = query.filter(Course.title == params.title)
        if params.description is not None:
            query = query.filter(Course.description.ilike(f"%{params.description}%"))
        if params.path is not None:
            # Convert string to Ltree for proper comparison
            query = query.filter(Course.path == Ltree(params.path))
        if params.course_family_id is not None:
            query = query.filter(Course.course_family_id == params.course_family_id)
        if params.organization_id is not None:
            query = query.filter(Course.organization_id == params.organization_id)
        if params.language_code is not None:
            query = query.filter(Course.language_code == params.language_code)
        # Both of these were declared on CourseQuery (and generated into the
        # clients) without a clause here, so the filters were silently ignored.
        if params.visible is not None:
            query = query.filter(Course.visible.is_(params.visible))
        if params.public is not None:
            query = query.filter(Course.public.is_(params.public))

        return query
