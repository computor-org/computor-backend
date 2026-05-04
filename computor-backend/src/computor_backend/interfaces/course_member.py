"""Backend CourseMember interface with SQLAlchemy model."""

from typing import Optional, Any
from uuid import UUID
from sqlalchemy.orm import Session
import logging

from computor_types.course_members import (
    CourseMemberInterface as CourseMemberInterfaceBase,
    CourseMemberQuery,
    CourseMemberUpdate,
)
from computor_backend.interfaces.base import BackendEntityInterface, CacheTag
from computor_backend.model.course import CourseMember
from computor_backend.permissions.principal import Principal, course_role_hierarchy
from computor_backend.api.exceptions import ForbiddenException

logger = logging.getLogger(__name__)


async def post_create_course_member(course_member: CourseMember, db: Session):
    """Post-create hook for CourseMember (CrudRouter).

    Delegates to the shared ``course_member_post_create`` function and
    additionally busts the course's dashboard caches so the freshly
    added member's role is reflected in tutor/lecturer/student views
    without waiting for TTL.
    """
    from computor_backend.business_logic.course_member_post_create import course_member_post_create
    await course_member_post_create(course_member, db)

    from computor_backend.business_logic.messages import invalidate_course_dashboards
    from computor_backend.redis_cache import get_cache

    invalidate_course_dashboards(course_member.course_id, get_cache())


async def post_update_course_member(
    course_member: CourseMember,
    old_course_member: CourseMember,
    db: Session,
) -> None:
    """Post-update hook for CourseMember.

    Bust dashboard caches when the change affects who sees what — i.e.
    a role change (student promoted to tutor) or a group reassignment.
    Other field updates (e.g. profile metadata) don't shift visibility,
    so we skip the cache bust to avoid unnecessary invalidation churn.
    """
    role_changed = (
        getattr(course_member, "course_role_id", None)
        != getattr(old_course_member, "course_role_id", None)
    )
    group_changed = (
        getattr(course_member, "course_group_id", None)
        != getattr(old_course_member, "course_group_id", None)
    )
    if not (role_changed or group_changed):
        return

    from computor_backend.business_logic.messages import invalidate_course_dashboards
    from computor_backend.redis_cache import get_cache

    invalidate_course_dashboards(course_member.course_id, get_cache())


def custom_permissions_course_member(
    permissions: Principal,
    db: Session,
    id: UUID,
    entity: CourseMemberUpdate
):
    """
    Custom permission check for CourseMember updates.
    Replaces generic check_permissions to enforce course-role-based authorization.

    Validates:
    1. User has at least _lecturer role in the course
    2. User can only assign roles <= their own level
    3. User cannot modify their own role (unless admin)

    Args:
        permissions: Current user's permission context
        db: Database session
        id: CourseMember ID being updated
        entity: Update data

    Returns:
        SQLAlchemy query filtered to the target course member

    Raises:
        ForbiddenException: If permission denied
    """
    # Admin bypasses all checks
    if permissions.is_admin:
        return db.query(CourseMember)

    # Get the course member being updated
    course_member = db.query(CourseMember).filter(CourseMember.id == id).first()
    if not course_member:
        # Return query that will find nothing - let crud.py handle NotFoundException
        return db.query(CourseMember).filter(CourseMember.id == id)

    course_id = str(course_member.course_id)

    # Check user has at least _lecturer role in this course
    user_role = permissions.get_highest_course_role(course_id)
    if not user_role or course_role_hierarchy.get_role_level(user_role) < course_role_hierarchy.get_role_level("_lecturer"):
        raise ForbiddenException(
            "You don't have permission to update course members. "
            "Lecturer role or higher is required."
        )

    # Check if trying to modify their own course role
    if str(course_member.user_id) == permissions.user_id:
        raise ForbiddenException(
            "You cannot modify your own course membership. Please contact an administrator."
        )

    # Check if target course member has equal or higher role - cannot modify peers or superiors
    target_current_role = course_member.course_role_id
    if target_current_role:
        target_current_level = course_role_hierarchy.get_role_level(target_current_role)
        user_level = course_role_hierarchy.get_role_level(user_role)
        if target_current_level >= user_level:
            raise ForbiddenException(
                f"You cannot modify a course member with role '{target_current_role}'. "
                f"Your role '{user_role}' can only modify members with lower privilege levels."
            )

    # If updating course_role_id, validate role escalation
    if hasattr(entity, 'course_role_id') and entity.course_role_id is not None:
        target_role = entity.course_role_id
        if not course_role_hierarchy.can_assign_role(user_role, target_role):
            raise ForbiddenException(
                f"You cannot assign the role '{target_role}'. "
                f"Your role '{user_role}' can only assign roles at or below your privilege level."
            )

    # Return query for the specific course member
    return db.query(CourseMember)


class CourseMemberInterface(CourseMemberInterfaceBase, BackendEntityInterface):
    """Backend-specific CourseMember interface with model attached."""

    model = CourseMember
    endpoint = "course-members"
    cache_ttl = 300
    post_create = post_create_course_member
    post_update = post_update_course_member
    custom_permissions = custom_permissions_course_member

    @classmethod
    def cache_invalidation_tags(cls, entity):
        """Course-membership changes flip a user's role-aware list views.

        Default impl emits ``user:<id>`` and ``course_id:<id>`` tags. We
        also need the three role-specific course-view tags so other
        users observing the roster (lecturer dashboards, etc.) refresh.
        """
        yield from super().cache_invalidation_tags(entity)
        if entity.course_id is not None:
            cid = str(entity.course_id)
            for view_tag in ("student_view", "tutor_view", "lecturer_view"):
                yield CacheTag.for_entity(view_tag, cid)

    @staticmethod
    def search(db: Session, query, params: Optional[CourseMemberQuery]):
        """
        Apply search filters to coursemember query.

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
            query = query.filter(CourseMember.id == params.id)
        if params.user_id is not None:
            query = query.filter(CourseMember.user_id == params.user_id)
        if params.course_id is not None:
            query = query.filter(CourseMember.course_id == params.course_id)
        if params.course_group_id is not None:
            query = query.filter(CourseMember.course_group_id == params.course_group_id)
        if params.course_role_id is not None:
            query = query.filter(CourseMember.course_role_id == params.course_role_id)

        return query
