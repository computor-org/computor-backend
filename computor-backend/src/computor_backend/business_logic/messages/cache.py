"""Dashboard / unread-count cache invalidation for message create/delete
and read-status changes."""
from uuid import UUID
from typing import Optional
from sqlalchemy.orm import Session

from computor_backend.model.message import Message
from computor_backend.model.course import (
    Course,
    CourseContent,
    CourseGroup,
    CourseMember,
    SubmissionGroup,
)
from computor_backend.cache import Cache


def invalidate_dashboard_views_for_message(
    message: Message,
    db: Session,
    cache: Optional[Cache] = None,
) -> None:
    """Clear cached student/tutor/lecturer dashboard views affected by a
    message create/delete.

    Every dashboard's ``unread_message_count`` badge depends on the set
    of non-archived messages visible to the viewer. When a message is
    posted (or soft-deleted) we have to bust the per-course view tags
    so the next fetch recomputes the badge.

    Scope -> affected courses:

    * ``submission_group``, ``course_content``, ``course_group``,
      ``course_member`` -> single course (resolved via lookup if the
      message itself doesn't carry ``course_id``)
    * ``course`` -> the course itself
    * ``course_family`` -> every course in that family (cascade)
    * ``organization`` -> every course in that org (cascade)
    * ``user_id`` -> none (direct chat doesn't surface in course
      dashboards)
    * global -> none (global posts don't refresh per-course badges; the
      inbox sidebar handles them via the ``user:<id>`` WS channel)

    For each affected course, three tags are busted:
    ``tutor_view:<id>``, ``lecturer_view:<id>``, ``student_view:<id>``.

    Read/unread state changes are per-user and handled separately by
    ``_invalidate_message_cache``.
    """
    if cache is None or message is None:
        return

    for course_id in _affected_course_ids_for_message(message, db):
        invalidate_course_dashboards(course_id, cache)


# Back-compat alias — older imports still resolve. Remove once all
# call sites use the new name.
invalidate_tutor_lecturer_views_for_message = invalidate_dashboard_views_for_message


def invalidate_course_dashboards(course_id, cache: Optional[Cache] = None) -> None:
    """Bust the three dashboard view caches for a course.

    Called from message create/delete (via
    ``invalidate_dashboard_views_for_message``) and from CourseMember
    create/update so role changes are immediately reflected in any
    cached dashboards (otherwise a freshly-promoted tutor would see
    the old student-level view until TTL expires).
    """
    if cache is None or course_id is None:
        return
    cid = str(course_id)
    cache.invalidate_tags(f"tutor_view:{cid}")
    cache.invalidate_tags(f"lecturer_view:{cid}")
    cache.invalidate_tags(f"student_view:{cid}")


def _affected_course_ids_for_message(message: Message, db: Session) -> set[str]:
    """Resolve the set of courses whose dashboards a message affects.

    Centralised here so the invalidator and any future broadcast/cache
    helpers share the same scope -> courses mapping. Returns string IDs;
    callers don't need to care whether the message had ``course_id`` set
    directly or whether it was resolved via a parent scope.
    """
    if message.course_id:
        return {str(message.course_id)}

    if message.submission_group_id:
        cid = db.query(SubmissionGroup.course_id).filter(
            SubmissionGroup.id == message.submission_group_id
        ).scalar()
        return {str(cid)} if cid else set()

    if message.course_content_id:
        cid = db.query(CourseContent.course_id).filter(
            CourseContent.id == message.course_content_id
        ).scalar()
        return {str(cid)} if cid else set()

    if message.course_group_id:
        cid = db.query(CourseGroup.course_id).filter(
            CourseGroup.id == message.course_group_id
        ).scalar()
        return {str(cid)} if cid else set()

    if message.course_member_id:
        cid = db.query(CourseMember.course_id).filter(
            CourseMember.id == message.course_member_id
        ).scalar()
        return {str(cid)} if cid else set()

    if message.course_family_id:
        rows = db.query(Course.id).filter(
            Course.course_family_id == message.course_family_id
        ).all()
        return {str(r[0]) for r in rows}

    if message.organization_id:
        rows = db.query(Course.id).filter(
            Course.organization_id == message.organization_id
        ).all()
        return {str(r[0]) for r in rows}

    # user_id (direct chat) and global — no per-course dashboards to bust.
    return set()


def _invalidate_message_cache(
    message_id: UUID | str,
    reader_user_id: str,
    db: Session,
    cache: Optional[Cache] = None,
) -> None:
    """
    Invalidate cached views when a message's read status changes.

    This function invalidates caches for the specific user who marked the message as read/unread,
    since unread message counts are user-specific and appear in student/tutor course content views.

    Strategy:
    - Invalidate all user views for the reader (safest approach for unread counts)
    - Additionally invalidate specific entity tags for broader cache coherence

    Args:
        message_id: Message ID
        reader_user_id: User ID who read/unread the message
        db: Database session
        cache: Optional cache instance
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"_invalidate_message_cache called: message_id={message_id}, reader_user_id={reader_user_id}, cache={cache is not None}")

    if not cache:
        logger.warning("Cache is None, skipping invalidation")
        return

    # Fetch the message to get its target fields
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        return

    # CRITICAL: Invalidate ALL cached views for this user
    # This is necessary because unread message counts appear in course content lists,
    # and those views are cached with complex query parameters and related_ids.
    # The safest approach is to invalidate all views for the user.
    logger.info(f"Invalidating user views for user_id={reader_user_id}")
    cache.invalidate_user_views(user_id=str(reader_user_id))
    logger.info(f"User views invalidated for user_id={reader_user_id}")

    # Additionally, invalidate entity-specific tags for broader cache coherence
    # (in case other users' caches reference these entities)

    if message.submission_group_id:
        # Invalidate submission group entity tags
        logger.info(f"Invalidating submission_group:{message.submission_group_id}")
        cache.invalidate_tags(f"submission_group:{message.submission_group_id}")

    if message.course_content_id:
        # Invalidate course content entity tags
        cache.invalidate_tags(f"course_content:{message.course_content_id}")
        cache.invalidate_tags(f"course_content_id:{message.course_content_id}")

    if message.course_member_id:
        # Invalidate course member entity tags
        cache.invalidate_tags(f"course_member:{message.course_member_id}")
        cache.invalidate_tags(f"course_member_id:{message.course_member_id}")

    if message.course_group_id:
        # Invalidate course group entity tags
        cache.invalidate_tags(f"course_group:{message.course_group_id}")
        cache.invalidate_tags(f"course_group_id:{message.course_group_id}")

    if message.course_id:
        # Invalidate course-level entity tags
        cache.invalidate_tags(f"course:{message.course_id}")
        cache.invalidate_tags(f"course_id:{message.course_id}")

    if message.user_id:
        # Invalidate user-specific entity tags
        cache.invalidate_tags(f"user:{message.user_id}")

    if message.course_family_id:
        # Course-family scope — bust both the entity tag (any cached
        # family-keyed view) and the dashboard tags of every course
        # inside that family, since the unread badge for those courses
        # depends on family-scoped messages too.
        cache.invalidate_tags(f"course_family:{message.course_family_id}")
        cache.invalidate_tags(f"course_family_id:{message.course_family_id}")

    if message.organization_id:
        cache.invalidate_tags(f"organization:{message.organization_id}")
        cache.invalidate_tags(f"organization_id:{message.organization_id}")
