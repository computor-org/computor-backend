"""Whether the deployment's tutor agent (Lena) serves a course (issues#618).

The tutor agent only answers in courses where its user is a member with the
``_tutor`` role, and a new course has no such member: until someone added
Lena by hand, ``@Lena`` in that course went unanswered with no hint why. This
puts the switch on the course. ``GET``/``PUT /courses/{id}/tutor-agent`` read
and set it, and the web UI offers it as a checkbox when a course is created
and on its edit page.

The agent is ``TUTOR_AGENT_USER_ID``; a deployment without one, or whose user
is archived or banned, reports ``available: false`` and refuses the switch.

Turning it on adds a ``_tutor`` membership. A membership with a higher role,
given by hand in the member list, already counts as enrolled and is left
alone. Turning it off removes only a ``_tutor`` membership, under the same
guards as removing a member from the list; any other role is changed there.
"""

import logging
from types import SimpleNamespace
from typing import Optional

from sqlalchemy.orm import Session

from computor_backend.exceptions import BadRequestException, NotFoundException
from computor_backend.model.auth import User
from computor_backend.model.course import Course, CourseMember
from computor_backend.permissions.core import check_course_permissions
from computor_backend.permissions.principal import Principal, course_role_hierarchy
from computor_backend.settings import settings
from computor_types.courses import CourseTutorAgentGet

logger = logging.getLogger(__name__)

TUTOR_ROLE_ID = "_tutor"
# Changing who teaches a course is a _lecturer decision, like the member list.
MANAGE_MIN_ROLE = "_lecturer"


def tutor_agent_user(db: Session) -> Optional[User]:
    """The configured tutor agent, if it is an active user."""
    if not settings.TUTOR_AGENT_USER_ID:
        return None
    return (
        db.query(User)
        .filter(
            User.id == settings.TUTOR_AGENT_USER_ID,
            User.archived_at.is_(None),
            User.banned_at.is_(None),
        )
        .first()
    )


def tutor_agent_name(user: User) -> str:
    # The account's given name is renamed to "Lena" on deployment
    # (docs/tutor-mentions.md); older accounts may still carry another label.
    return user.given_name or "Lena"


def _course_for_manager(course_id: str, principal: Principal, db: Session) -> Course:
    course = (
        check_course_permissions(principal, Course, MANAGE_MIN_ROLE, db)
        .filter(Course.id == course_id)
        .first()
    )
    if course is None:
        raise NotFoundException(
            detail="Course not found",
            context={"course_id": course_id},
        )
    return course


def _membership(user_id, course_id: str, db: Session) -> Optional[CourseMember]:
    return (
        db.query(CourseMember)
        .filter(CourseMember.user_id == str(user_id), CourseMember.course_id == course_id)
        .first()
    )


def _serves(member: Optional[CourseMember]) -> bool:
    return member is not None and course_role_hierarchy.get_role_level(
        member.course_role_id
    ) >= course_role_hierarchy.get_role_level(TUTOR_ROLE_ID)


def _status(agent: Optional[User], member: Optional[CourseMember]) -> CourseTutorAgentGet:
    if agent is None:
        return CourseTutorAgentGet(available=False, enrolled=False)
    return CourseTutorAgentGet(
        available=True,
        enrolled=_serves(member),
        course_role_id=member.course_role_id if member is not None else None,
        name=tutor_agent_name(agent),
    )


def get_course_tutor_agent(course_id: str, principal: Principal, db: Session) -> CourseTutorAgentGet:
    course = _course_for_manager(str(course_id), principal, db)
    agent = tutor_agent_user(db)
    member = _membership(agent.id, str(course.id), db) if agent is not None else None
    return _status(agent, member)


async def set_course_tutor_agent(
    course_id: str,
    enrolled: bool,
    principal: Principal,
    db: Session,
) -> CourseTutorAgentGet:
    """Enrol the tutor agent as ``_tutor`` in the course, or remove it again.

    Idempotent: asking for the current state changes nothing. Commits itself,
    so the caches dropped afterwards cannot be refilled from a pre-commit read.
    """
    course = _course_for_manager(str(course_id), principal, db)
    cid = str(course.id)
    agent = tutor_agent_user(db)
    if agent is None:
        raise BadRequestException(
            detail="This deployment has no AI tutor configured (TUTOR_AGENT_USER_ID).",
        )
    name = tutor_agent_name(agent)
    member = _membership(agent.id, cid, db)

    if enrolled:
        if _serves(member):
            return _status(agent, member)
        if member is not None:
            raise BadRequestException(
                detail=(
                    f"{name} is a member of this course with the role "
                    f"'{member.course_role_id}'. Change the role in the member list."
                ),
                context={"course_role_id": member.course_role_id},
            )
        member = CourseMember(
            user_id=str(agent.id),
            course_id=cid,
            course_role_id=TUTOR_ROLE_ID,
            created_by=principal.user_id,
            updated_by=principal.user_id,
        )
        db.add(member)
        db.commit()
        _after_change(member.user_id, cid)
        await _run_post_create(member, db)
        logger.info("Enrolled tutor agent %s as %s of course %s", agent.id, TUTOR_ROLE_ID, cid)
        return _status(agent, member)

    if member is None:
        return _status(agent, None)
    if member.course_role_id != TUTOR_ROLE_ID:
        raise BadRequestException(
            detail=(
                f"{name} has the role '{member.course_role_id}' in this course, "
                "given in the member list. Remove it there."
            ),
            context={"course_role_id": member.course_role_id},
        )
    _guard_removal(member, db)
    user_id = str(member.user_id)
    db.delete(member)
    db.commit()
    _after_change(user_id, cid)
    logger.info("Removed tutor agent %s from course %s", agent.id, cid)
    return _status(agent, None)


def _guard_removal(member: CourseMember, db: Session) -> None:
    """The member-list delete's guards (``crud.delete_entity``), so this
    switch cannot take what removing the member there would refuse to."""
    from computor_backend.business_logic.crud import (
        _count_messages_of_others_lost,
        _release_submission_groups,
    )
    from computor_backend.model.message import Message

    lost = _count_messages_of_others_lost(
        db, Message.course_member_id == member.id, member.user_id,
    )
    if lost:
        raise BadRequestException(
            detail=f"Cannot remove the AI tutor because messages written by others would be deleted with it (messages: {lost}).",
            context={"message_count": lost},
        )
    blocking = _release_submission_groups([member.id], db)
    if blocking:
        raise BadRequestException(
            detail=f"Cannot remove the AI tutor because its submission groups hold submissions, results or messages (groups: {blocking}).",
            context={"submission_group_count": blocking},
        )


def _after_change(user_id: str, course_id: str) -> None:
    """Drop the views the member list's CRUD path drops for a membership change.

    Principals are marked stale by the session's commit hook
    (``database._track_permission_membership_writes``). Best-effort: a stale
    cache must never fail a write that already landed.
    """
    from computor_backend.business_logic.course_ownership import (
        invalidate_user_membership_caches,
    )
    from computor_backend.business_logic.messages import invalidate_course_dashboards
    from computor_backend.interfaces.course_member import CourseMemberInterface
    from computor_backend.redis_cache import get_cache

    invalidate_user_membership_caches(user_id)
    try:
        cache = get_cache()
        # Tags are read off ids only; the row itself may be gone.
        row = SimpleNamespace(
            id=None, user_id=user_id, course_id=course_id, course_group_id=None,
        )
        for tag in CourseMemberInterface.cache_invalidation_tags(row):
            cache.invalidate_user_views(
                user_id=tag.user_id,
                entity_type=tag.entity_type,
                entity_id=tag.entity_id,
            )
        invalidate_course_dashboards(course_id, cache)
    except Exception:
        logger.warning(
            "Cache invalidation after the tutor agent change in course %s failed",
            course_id,
            exc_info=True,
        )


async def _run_post_create(member: CourseMember, db: Session) -> None:
    """The member list's post-create hook. It skips service accounts, which
    the tutor agent normally is, but a deployment may use a plain user."""
    from computor_backend.business_logic.course_member_post_create import (
        course_member_post_create,
    )

    try:
        await course_member_post_create(member, db)
    except Exception:
        logger.exception(
            "Post-create steps for the tutor agent in course %s failed",
            member.course_id,
        )
