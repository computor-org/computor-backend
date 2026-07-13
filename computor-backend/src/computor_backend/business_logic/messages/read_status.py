"""Per-user read status, author enrichment and read/unread mutations."""
from uuid import UUID
from typing import Optional, Tuple, List, Dict
from sqlalchemy.orm import Session

from computor_backend.permissions.principal import Principal
from computor_backend.model.message import MessageRead, Message
from computor_backend.model.course import CourseMember
from computor_backend.model.auth import User
from computor_backend.cache import Cache
from computor_types.messages import (
    MessageGet, MessageAuthor, MessageAuthorCourseMember, MessageMentionRef,
)
from .mentions import _get_mentions_info
from .cache import _invalidate_message_cache


def mark_author_as_reader(
    message_id: UUID | str,
    author_id: UUID | str,
    db: Session,
) -> None:
    """Stamp the message's author as having read it.

    Without this, an author's inbox always shows their own freshly
    posted message as unread. We sidestep ``mark_message_as_read``
    deliberately here — that helper does cache invalidation that is
    redundant inside the create flow (the dashboard caches are already
    busted by ``invalidate_dashboard_views_for_message`` and the
    author's WS clients learn about the new message via the per-user
    inbox channel).

    Idempotent: a duplicate insert is silently swallowed via rollback,
    so the create path never fails because of a race with a manual
    mark-read.
    """
    from sqlalchemy.exc import IntegrityError

    try:
        db.add(MessageRead(message_id=message_id, reader_user_id=author_id))
        db.commit()
    except IntegrityError:
        db.rollback()


def get_message_with_read_status(
    message_id: UUID | str,
    message: MessageGet,
    permissions: Principal,
    db: Session,
) -> MessageGet:
    """Get a message with read status, author status, and author details.

    Args:
        message_id: Message ID
        message: Message entity from get_id_db
        permissions: Current user permissions
        db: Database session

    Returns:
        Message with is_read, is_author, is_deleted, deleted_by,
        author, and author_course_member fields populated
    """
    reader_user_id = permissions.user_id
    is_read = False
    is_author = False

    if reader_user_id:
        exists = (
            db.query(MessageRead.id)
            .filter(
                MessageRead.message_id == message_id,
                MessageRead.reader_user_id == reader_user_id,
            )
            .first()
        )
        is_read = exists is not None

        # Check if the current user is the author
        is_author = str(message.author_id) == str(reader_user_id)

    # Get deletion status and author info from database
    db_message = db.query(Message).filter(Message.id == message_id).first()
    is_deleted = db_message.is_deleted if db_message else False
    deleted_by = db_message.deleted_by if db_message and db_message.is_deleted else None

    # Get author info
    author = None
    author_course_member = None

    mentions: List[MessageMentionRef] = []
    if db_message:
        author_map, author_course_member_map = _get_author_info([db_message], db)
        author = author_map.get(str(message_id))
        author_course_member = author_course_member_map.get(str(message_id))
        mentions = _get_mentions_info([db_message], db).get(str(message_id), [])

    return message.model_copy(update={
        "is_read": is_read,
        "is_author": is_author,
        "is_deleted": is_deleted,
        "deleted_by": deleted_by,
        "author": author,
        "author_course_member": author_course_member,
        "mentions": mentions,
    })


def _get_author_info(
    db_messages: List[Message],
    db: Session,
) -> Tuple[Dict[str, MessageAuthor], Dict[str, Optional[MessageAuthorCourseMember]]]:
    """Get author info for a batch of messages.

    Args:
        db_messages: List of Message model instances
        db: Database session

    Returns:
        Tuple of (author_map, author_course_member_map)
        - author_map: dict mapping message_id -> MessageAuthor
        - author_course_member_map: dict mapping message_id -> MessageAuthorCourseMember or None
    """
    if not db_messages:
        return {}, {}

    # Collect unique author_ids
    author_ids = list(set(str(msg.author_id) for msg in db_messages))

    # Fetch all authors
    authors = db.query(User).filter(User.id.in_(author_ids)).all()
    author_user_map = {str(u.id): u for u in authors}

    # Build author info map
    author_map: Dict[str, MessageAuthor] = {}
    for msg in db_messages:
        msg_id = str(msg.id)
        author_id = str(msg.author_id)
        user = author_user_map.get(author_id)
        if user:
            author_map[msg_id] = MessageAuthor(
                id=author_id,
                given_name=user.given_name,
                family_name=user.family_name
            )

    # For course-scoped messages, find author's course membership
    # Course-scoped = has any of: organization_id, course_family_id, course_id, course_content_id,
    #                 course_group_id, submission_group_id, course_member_id (but not just user_id or global)
    author_course_member_map: Dict[str, Optional[MessageAuthorCourseMember]] = {}

    for msg in db_messages:
        msg_id = str(msg.id)
        author_course_member_map[msg_id] = None

        # Determine if this is a course-scoped message
        course_id = None

        if msg.course_id:
            course_id = msg.course_id
        elif msg.course_content_id and msg.course_content:
            course_id = msg.course_content.course_id
        elif msg.course_group_id and msg.course_group:
            course_id = msg.course_group.course_id
        elif msg.submission_group_id and msg.submission_group:
            course_id = msg.submission_group.course_id
        elif msg.course_member_id and msg.course_member:
            course_id = msg.course_member.course_id
        elif msg.course_family_id:
            # Course family level - no specific course membership
            pass
        elif msg.organization_id:
            # Organization level - no specific course membership
            pass

        if course_id:
            # Find author's course membership for this course
            course_member = db.query(CourseMember).filter(
                CourseMember.user_id == msg.author_id,
                CourseMember.course_id == course_id
            ).first()

            if course_member:
                author_course_member_map[msg_id] = MessageAuthorCourseMember(
                    id=str(course_member.id),
                    course_role_id=course_member.course_role_id,
                    course_id=str(course_id)
                )

    return author_map, author_course_member_map


def list_messages_with_read_status(
    items: list[MessageGet],
    permissions: Principal,
    db: Session,
) -> list[MessageGet]:
    """Add read status, author status, and author details to a list of messages.

    Args:
        items: List of messages
        permissions: Current user permissions
        db: Database session

    Returns:
        List of messages with is_read, is_author, is_deleted, deleted_by,
        author, and author_course_member fields populated
    """
    reader_user_id = permissions.user_id

    if not items:
        return []

    message_ids = [item.id for item in items]

    # Get read status
    if reader_user_id:
        read_rows = (
            db.query(MessageRead.message_id)
            .filter(
                MessageRead.reader_user_id == reader_user_id,
                MessageRead.message_id.in_(message_ids),
            )
            .all()
        )
        read_ids = {str(row[0]) for row in read_rows}
    else:
        read_ids = set()

    # Get deletion status and author info from database messages
    db_messages = db.query(Message).filter(Message.id.in_(message_ids)).all()
    db_message_map = {str(msg.id): msg for msg in db_messages}

    deletion_map = {
        str(msg.id): {
            "is_deleted": msg.is_deleted,
            "deleted_by": msg.deleted_by if msg.is_deleted else None
        }
        for msg in db_messages
    }

    # Get author info
    author_map, author_course_member_map = _get_author_info(db_messages, db)
    mentions_map = _get_mentions_info(db_messages, db)

    return [
        item.model_copy(update={
            "is_read": item.id in read_ids,
            "is_author": str(item.author_id) == str(reader_user_id) if reader_user_id else False,
            "is_deleted": deletion_map.get(item.id, {}).get("is_deleted", False),
            "deleted_by": deletion_map.get(item.id, {}).get("deleted_by"),
            "author": author_map.get(item.id),
            "author_course_member": author_course_member_map.get(item.id),
            "mentions": mentions_map.get(item.id, []),
        })
        for item in items
    ]


def mark_message_as_read(
    message_id: UUID | str,
    permissions: Principal,
    db: Session,
    cache: Optional[Cache] = None,
) -> None:
    """Mark a message as read for the current user.

    Args:
        message_id: Message ID
        permissions: Current user permissions
        db: Database session
        cache: Optional cache instance for invalidation
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"mark_message_as_read called: message_id={message_id}, user_id={permissions.user_id}, cache={cache is not None}")

    # Upsert read record for current user
    exists = (
        db.query(MessageRead)
        .filter(MessageRead.message_id == message_id, MessageRead.reader_user_id == permissions.user_id)
        .first()
    )
    if not exists:
        logger.info(f"Creating new MessageRead record for message_id={message_id}, user_id={permissions.user_id}")
        db.add(MessageRead(message_id=message_id, reader_user_id=permissions.user_id))
        db.commit()

        # Invalidate cached views that include unread message counts
        _invalidate_message_cache(message_id, str(permissions.user_id), db, cache)
    else:
        logger.info(f"Message {message_id} already marked as read by user {permissions.user_id}")


def mark_message_as_unread(
    message_id: UUID | str,
    permissions: Principal,
    db: Session,
    cache: Optional[Cache] = None,
) -> None:
    """Mark a message as unread for the current user.

    Args:
        message_id: Message ID
        permissions: Current user permissions
        db: Database session
        cache: Optional cache instance for invalidation
    """
    read = (
        db.query(MessageRead)
        .filter(MessageRead.message_id == message_id, MessageRead.reader_user_id == permissions.user_id)
        .first()
    )
    if read:
        db.delete(read)
        db.commit()

        # Invalidate cached views that include unread message counts
        _invalidate_message_cache(message_id, str(permissions.user_id), db, cache)
