"""Per-user read status, author enrichment and read/unread mutations."""
from uuid import UUID
from typing import Optional, Tuple, List, Dict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from computor_backend.permissions.core import check_permissions
from computor_backend.permissions.principal import Principal
from computor_backend.model.message import MessageRead, Message
from computor_backend.model.course import CourseMember
from computor_backend.model.auth import User
from computor_backend.cache import Cache
from computor_types.messages import (
    MessageGet, MessageAuthor, MessageAuthorCourseMember, MessageMentionRef,
)
from .audience import course_ids_for_messages
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

    # For course-scoped messages, attach the author's membership in that
    # course. Both halves are batched: the message->course resolution (one
    # query per target type) and the membership lookup (one query for the
    # whole page). This used to be a lazy-load plus a CourseMember query
    # *per message*, and the list endpoint runs it over every row returned.
    author_course_member_map: Dict[str, Optional[MessageAuthorCourseMember]] = {
        str(msg.id): None for msg in db_messages
    }

    course_by_message = course_ids_for_messages(db_messages, db)

    wanted = {
        (str(msg.author_id), str(course_by_message[str(msg.id)]))
        for msg in db_messages
        if course_by_message.get(str(msg.id))
    }
    if not wanted:
        return author_map, author_course_member_map

    membership_by_pair = {
        (str(user_id), str(course_id)): (cm_id, role_id)
        for cm_id, user_id, course_id, role_id in db.query(
            CourseMember.id,
            CourseMember.user_id,
            CourseMember.course_id,
            CourseMember.course_role_id,
        ).filter(
            CourseMember.user_id.in_({author for author, _ in wanted}),
            CourseMember.course_id.in_({course for _, course in wanted}),
        ).all()
    }

    for msg in db_messages:
        course_id = course_by_message.get(str(msg.id))
        if not course_id:
            continue
        membership = membership_by_pair.get((str(msg.author_id), str(course_id)))
        if membership:
            cm_id, role_id = membership
            author_course_member_map[str(msg.id)] = MessageAuthorCourseMember(
                id=str(cm_id),
                course_role_id=role_id,
                course_id=str(course_id),
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


def mark_messages_as_read(
    message_ids: List[str],
    permissions: Principal,
    db: Session,
    cache: Optional[Cache] = None,
) -> List[Message]:
    """Mark many messages read for the current user in one pass.

    Opening a thread marks everything in it read, which used to mean one
    request per message — each one writing a row, calling
    ``cache.invalidate_user_views`` (which drops *every* cached view for
    that user, not just the message-bearing ones) and publishing two Redis
    events. A panel with 200 unread did all of that 200 times, which is
    why the inbox had to grow a concurrency limiter and a WS-suppression
    window just to survive its own read sweep.

    Only messages the caller can actually see are marked; ids they cannot
    read are silently skipped rather than 403-ing the whole batch, since a
    sweep is best-effort by nature and the caller learns nothing from an
    id it was never shown.

    Returns the Message rows newly marked read (already-read ones are
    excluded), so the caller can broadcast per scope channel.
    """
    if not message_ids:
        return []

    unique_ids = list(dict.fromkeys(str(mid) for mid in message_ids))

    # Narrow to what this principal may read, in one query.
    visible_query = check_permissions(permissions, Message, "get", db)
    if visible_query is None:
        return []
    visible = (
        visible_query
        .filter(Message.id.in_(unique_ids), Message.archived_at.is_(None))
        .all()
    )
    if not visible:
        return []

    already_read = {
        str(row[0])
        for row in db.query(MessageRead.message_id)
        .filter(
            MessageRead.reader_user_id == permissions.user_id,
            MessageRead.message_id.in_([str(m.id) for m in visible]),
        )
        .all()
    }

    newly_read = [m for m in visible if str(m.id) not in already_read]
    if not newly_read:
        return []

    db.add_all([
        MessageRead(message_id=m.id, reader_user_id=permissions.user_id)
        for m in newly_read
    ])
    try:
        db.commit()
    except IntegrityError:
        # Raced with a concurrent single mark-read for one of these ids.
        # The unique index did its job; fall back to per-row inserts so
        # the rest of the batch still lands.
        db.rollback()
        newly_read = _insert_reads_individually(newly_read, permissions, db)
        if not newly_read:
            return []

    # One invalidation for the whole batch instead of one per message.
    _invalidate_message_cache_bulk(newly_read, str(permissions.user_id), cache)

    return newly_read


def _insert_reads_individually(
    messages: List[Message],
    permissions: Principal,
    db: Session,
) -> List[Message]:
    """Per-row fallback for the bulk insert; skips rows that now conflict."""
    inserted: List[Message] = []
    for message in messages:
        try:
            db.add(MessageRead(message_id=message.id, reader_user_id=permissions.user_id))
            db.commit()
            inserted.append(message)
        except IntegrityError:
            db.rollback()
    return inserted


def _invalidate_message_cache_bulk(
    messages: List[Message],
    reader_user_id: str,
    cache: Optional[Cache] = None,
) -> None:
    """Batch equivalent of ``_invalidate_message_cache``.

    ``invalidate_user_views`` is the expensive, blunt part and is
    user-scoped, so it runs exactly once no matter how many messages were
    read. The per-entity tags are deduped across the batch — a thread's
    messages nearly all share one target, so this collapses N tag drops
    into one.
    """
    if not cache or not messages:
        return

    cache.invalidate_user_views(user_id=reader_user_id)

    tags: set[str] = set()
    for message in messages:
        for scope in ("submission_group", "course_content", "course_member",
                      "course_group", "course", "course_family", "organization"):
            target_id = getattr(message, f"{scope}_id", None)
            if target_id:
                tags.add(f"{scope}:{target_id}")
                tags.add(f"{scope}_id:{target_id}")
        if message.user_id:
            tags.add(f"user:{message.user_id}")

    for tag in tags:
        cache.invalidate_tags(tag)


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
