"""Backend Course interface with SQLAlchemy model."""

import logging
from typing import Any, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session

from computor_types.courses import (
    CourseInterface as CourseInterfaceBase,
    CourseQuery,
)
from computor_types.custom_types import Ltree
from computor_backend.exceptions import ForbiddenException
from computor_backend.interfaces.base import BackendEntityInterface, CacheTag
from computor_backend.model.course import Course
from computor_backend.permissions.core import check_permissions
from computor_backend.permissions.principal import Principal, course_role_hierarchy
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


# Opening a course for self-registration is held above the _lecturer bar that
# the rest of Course.update sits on.
PUBLIC_FLAG_MIN_ROLE = "_maintainer"


def _guard_public_flag(permissions: Principal, db: Session, course_id: Any) -> None:
    """Only ``_maintainer`` and above may open or close a course (issue #213).

    Every other course setting is a _lecturer decision, but this one is not
    about the course, it is about the *instance*: a public course is advertised
    to every account on the deployment — including users from other
    organizations — and lets strangers create memberships in it. A lecturer can
    already enrol anyone they like, so the new power here is discoverability,
    which is an institutional call.

    Applies in both directions. Un-listing a course is the same kind of
    decision, and letting a lecturer close what a maintainer opened would be
    the same authority split in reverse.

    ``get_course_authority_ceiling`` already resolves admins and
    ``_organization_manager`` to ``_owner``, so they pass without a special
    case.
    """
    ceiling = permissions.get_course_authority_ceiling(str(course_id))
    if not ceiling or course_role_hierarchy.get_role_level(
        ceiling
    ) < course_role_hierarchy.get_role_level(PUBLIC_FLAG_MIN_ROLE):
        raise ForbiddenException(
            error_code="AUTHZ_004",
            detail=(
                "Opening a course for self-registration requires the "
                f"'{PUBLIC_FLAG_MIN_ROLE}' course role or higher. Your role "
                f"'{ceiling or '—'}' can change every other course setting."
            ),
            context={
                "course_id": str(course_id),
                "required_role": PUBLIC_FLAG_MIN_ROLE,
                "authority": ceiling,
            },
        )


def custom_permissions_course(permissions: Principal, db: Session, id, entity):
    """Course update permissions: the standard rules, plus the `public` guard.

    Replaces ``check_permissions`` on the update path (see
    ``business_logic.crud.update_entity``), so it must return the same
    permission-filtered query for every field it does not special-case —
    otherwise a lecturer would lose the ability to edit their own course.

    ``model_fields_set`` is what distinguishes "did not mention public" from
    "sent public=false": the backend applies updates with
    ``exclude_unset=True``, so only an explicitly supplied key is a change.
    """
    fields = (
        entity.model_fields_set
        if isinstance(entity, BaseModel)
        else set(entity or {})
    )
    if "public" in fields:
        _guard_public_flag(permissions, db, id)

    return check_permissions(permissions, Course, "update", db)


class CourseInterface(CourseInterfaceBase, BackendEntityInterface):
    """Backend-specific Course interface with model attached."""

    model = Course
    endpoint = "courses"
    cache_ttl = 300
    post_update = post_update_course
    custom_permissions = custom_permissions_course

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
