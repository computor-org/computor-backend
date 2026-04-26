"""Backend CourseFamily interface with SQLAlchemy model."""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from computor_types.course_families import (
    CourseFamilyInterface as CourseFamilyInterfaceBase,
    CourseFamilyQuery,
)
from computor_types.custom_types import Ltree
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.course import CourseFamily, CourseFamilyMember

logger = logging.getLogger(__name__)


async def post_create_course_family(course_family, db: Session):
    """Auto-grant the creating user ``_owner`` on the new course family."""
    if course_family is None or course_family.created_by is None:
        return
    try:
        existing = (
            db.query(CourseFamilyMember)
            .filter(
                CourseFamilyMember.user_id == course_family.created_by,
                CourseFamilyMember.course_family_id == course_family.id,
            )
            .first()
        )
        if existing is not None:
            return

        member = CourseFamilyMember(
            user_id=course_family.created_by,
            course_family_id=course_family.id,
            course_family_role_id="_owner",
            created_by=course_family.created_by,
            updated_by=course_family.created_by,
        )
        db.add(member)
        db.flush()
        logger.info(
            "Auto-assigned creator %s as _owner of course_family %s",
            course_family.created_by,
            course_family.id,
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "Failed to auto-assign creator as _owner for course_family %s",
            getattr(course_family, "id", None),
        )


class CourseFamilyInterface(CourseFamilyInterfaceBase, BackendEntityInterface):
    """Backend-specific CourseFamily interface with model attached."""

    model = CourseFamily
    endpoint = "course-families"
    cache_ttl = 600
    post_create = post_create_course_family

    @staticmethod
    def search(db: Session, query, params: Optional[CourseFamilyQuery]):
        """Apply search filters to course family query."""
        if params is None:
            return query

        if params.id is not None:
            query = query.filter(CourseFamily.id == params.id)
        if params.title is not None:
            query = query.filter(CourseFamily.title == params.title)
        if params.description is not None:
            query = query.filter(CourseFamily.description.ilike(f"%{params.description}%"))
        if params.path is not None:
            # Convert string to Ltree for proper comparison
            query = query.filter(CourseFamily.path == Ltree(params.path))
        if params.organization_id is not None:
            query = query.filter(CourseFamily.organization_id == params.organization_id)

        return query
