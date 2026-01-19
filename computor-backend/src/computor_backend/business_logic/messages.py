"""Business logic for message operations."""
from uuid import UUID
from typing import Optional, Tuple, List, Dict, Any
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from computor_backend.api.exceptions import BadRequestException, NotImplementedException, ForbiddenException
from computor_backend.permissions.principal import Principal
from computor_backend.permissions.core import check_permissions
from computor_backend.model.message import MessageRead, Message
from computor_backend.model.course import CourseMember, SubmissionGroup, SubmissionGroupMember
from computor_backend.model.auth import User
from computor_types.messages import (
    MessageCreate, MessageGet, MessageList, MessageQuery,
    MessageAuthor, MessageAuthorCourseMember
)
from computor_backend.cache import Cache


def create_message_with_author(
    payload: MessageCreate,
    permissions: Principal,
    db: Session,
) -> dict:
    """Create a message with enforced author_id and defaults.

    Permission rules per target:
    - user_id: NOT IMPLEMENTED - throws NotImplementedException
    - course_member_id: NOT IMPLEMENTED - throws NotImplementedException
    - submission_group_id: Writeable by submission_group_members and non-_student course roles
    - course_group_id: Read-only - throws ForbiddenException on create
    - course_content_id: LECTURER+ ONLY - requires _lecturer, _maintainer, or _owner role
    - course_id: LECTURER+ ONLY - requires _lecturer, _maintainer, or _owner role

    Args:
        payload: Message creation data
        permissions: Current user permissions
        db: Database session

    Returns:
        Dictionary with model_dump ready for create_db

    Raises:
        BadRequestException: If title or content missing
        NotImplementedException: If user_id or course_member_id target
        ForbiddenException: If trying to write to read-only target or lacking permissions
    """
    # Enforce author_id from current user
    if not payload.title or not payload.content:
        raise BadRequestException(detail="Title and content are required")

    model_dump = payload.model_dump(exclude_unset=True)
    model_dump['author_id'] = permissions.user_id

    # Validate target fields - messages should have a primary scope
    # Primary target fields (the most specific level)
    primary_target_fields = ['user_id', 'course_member_id', 'submission_group_id', 'course_group_id', 'course_content_id', 'course_id']
    set_targets = [k for k in primary_target_fields if model_dump.get(k)]

    # If parent_id is set, inherit target from parent message
    if model_dump.get('parent_id'):
        from computor_backend.model.message import Message
        parent_message = db.query(Message).filter(Message.id == model_dump['parent_id']).first()
        if not parent_message:
            raise BadRequestException(detail=f"Parent message {model_dump['parent_id']} not found")

        # Inherit target fields from parent
        for field in primary_target_fields:
            parent_value = getattr(parent_message, field, None)
            if parent_value is not None:
                # Don't override if user explicitly set a target (will be caught by validation below)
                if field not in model_dump or model_dump[field] is None:
                    model_dump[field] = parent_value

        # Recalculate set_targets after inheriting from parent
        set_targets = [k for k in primary_target_fields if model_dump.get(k)]

    # Determine the PRIMARY target (most specific)
    # Hierarchy from most specific to least: submission_group > course_content > course_group > course > course_family > organization
    # Allow course_id alongside more specific targets (for hierarchical context)
    primary_target = None
    if 'submission_group_id' in set_targets:
        primary_target = 'submission_group_id'
        # Remove course_id from set_targets - it's allowed as hierarchical context
        set_targets = [t for t in set_targets if t != 'course_id']
    elif 'course_content_id' in set_targets:
        primary_target = 'course_content_id'
        set_targets = [t for t in set_targets if t != 'course_id']
    elif 'course_group_id' in set_targets:
        primary_target = 'course_group_id'
        set_targets = [t for t in set_targets if t != 'course_id']
    elif 'course_id' in set_targets:
        primary_target = 'course_id'

    if len(set_targets) == 0:
        # Allow user-only message by setting user_id to current user if nothing else provided
        model_dump['user_id'] = permissions.user_id
        set_targets = ['user_id']
    elif len(set_targets) > 1:
        raise BadRequestException(detail=f"Only ONE target field should be set, but got: {', '.join(set_targets)}. Please specify only one of: user_id, course_member_id, submission_group_id, course_group_id, course_content_id, or course_id.")

    # Check target-specific write permissions
    if model_dump.get('user_id'):
        raise NotImplementedException(detail="Direct user messages (user_id target) are not implemented")

    if model_dump.get('course_member_id'):
        raise NotImplementedException(detail="Course member messages (course_member_id target) are not implemented")

    if model_dump.get('course_group_id'):
        raise ForbiddenException(detail="Cannot create messages directly to course_group_id (read-only target)")

    # submission_group_id: Check if user is a member or has elevated role
    if model_dump.get('submission_group_id'):
        submission_group_id = model_dump['submission_group_id']
        _check_submission_group_write_permission(permissions, submission_group_id, db)

        # Populate course_id from submission group for hierarchical broadcasting
        submission_group = db.query(SubmissionGroup).filter(
            SubmissionGroup.id == submission_group_id
        ).first()
        if submission_group and submission_group.course_id:
            model_dump['course_id'] = str(submission_group.course_id)

    # course_content_id: Check if user has submission group with that content
    if model_dump.get('course_content_id') and not model_dump.get('submission_group_id'):
        course_content_id = model_dump['course_content_id']
        _check_course_content_write_permission(permissions, course_content_id, db)

        # Populate course_id from course content for hierarchical broadcasting
        from computor_backend.model.course import CourseContent
        course_content = db.query(CourseContent).filter(
            CourseContent.id == course_content_id
        ).first()
        if course_content and course_content.course_id:
            model_dump['course_id'] = str(course_content.course_id)

    # course_id: Only check write permission if course_id was the PRIMARY target
    # (not derived from submission_group_id or course_content_id)
    if 'course_id' in set_targets:
        course_id = model_dump['course_id']
        _check_course_write_permission(permissions, course_id, db)

    # Default level
    if 'level' not in model_dump or model_dump['level'] is None:
        model_dump['level'] = 0

    return model_dump


def _check_submission_group_write_permission(
    permissions: Principal,
    submission_group_id: str,
    db: Session,
) -> None:
    """Check if user can write to a submission group.

    Rules:
    - User must be a submission_group_member OR
    - User must have a course role other than _student in the submission group's course

    Raises:
        ForbiddenException: If user lacks permission
    """
    # Check if user is a submission group member
    is_member = db.query(
        db.query(SubmissionGroupMember.id)
        .join(CourseMember, CourseMember.id == SubmissionGroupMember.course_member_id)
        .filter(
            SubmissionGroupMember.submission_group_id == submission_group_id,
            CourseMember.user_id == permissions.user_id
        )
        .exists()
    ).scalar()

    if is_member:
        return

    # Check if user has non-student role in the course
    submission_group = db.query(SubmissionGroup).filter(
        SubmissionGroup.id == submission_group_id
    ).first()

    if not submission_group:
        raise ForbiddenException(detail="Submission group not found")

    # Check course membership with elevated role
    has_elevated_role = db.query(
        db.query(CourseMember.id)
        .filter(
            CourseMember.course_id == submission_group.course_id,
            CourseMember.user_id == permissions.user_id,
            CourseMember.course_role_id != "_student"
        )
        .exists()
    ).scalar()

    if not has_elevated_role:
        raise ForbiddenException(detail="You must be a submission group member or have elevated course role to write messages to this submission group")


def _check_course_content_write_permission(
    permissions: Principal,
    course_content_id: str,
    db: Session,
) -> None:
    """Check if user can write to a course content.

    Only _lecturer and above can write to course_content_id.
    Students and tutors cannot write here.

    Raises:
        ForbiddenException: If user lacks permission
    """
    from computor_backend.model.course import CourseContent

    # Get the course_content to find the course
    course_content = db.query(CourseContent).filter(
        CourseContent.id == course_content_id
    ).first()

    if not course_content:
        raise ForbiddenException(detail="Course content not found")

    # Check if user has _lecturer or higher role in the course
    has_lecturer_role = db.query(
        db.query(CourseMember.id)
        .filter(
            CourseMember.course_id == course_content.course_id,
            CourseMember.user_id == permissions.user_id,
            CourseMember.course_role_id.in_(["_lecturer", "_maintainer", "_owner"])
        )
        .exists()
    ).scalar()

    if not has_lecturer_role:
        raise ForbiddenException()


def _check_course_write_permission(
    permissions: Principal,
    course_id: str,
    db: Session,
) -> None:
    """Check if user can write to a course.

    Only _lecturer and above can write to course_id.
    Students and tutors cannot write here.

    Raises:
        ForbiddenException: If user lacks permission
    """
    # Check if user has _lecturer or higher role in the course
    has_lecturer_role = db.query(
        db.query(CourseMember.id)
        .filter(
            CourseMember.course_id == course_id,
            CourseMember.user_id == permissions.user_id,
            CourseMember.course_role_id.in_(["_lecturer", "_maintainer", "_owner"])
        )
        .exists()
    ).scalar()

    if not has_lecturer_role:
        raise ForbiddenException()


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

    if db_message:
        author_map, author_course_member_map = _get_author_info([db_message], db)
        author = author_map.get(str(message_id))
        author_course_member = author_course_member_map.get(str(message_id))

    return message.model_copy(update={
        "is_read": is_read,
        "is_author": is_author,
        "is_deleted": is_deleted,
        "deleted_by": deleted_by,
        "author": author,
        "author_course_member": author_course_member,
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

    return [
        item.model_copy(update={
            "is_read": item.id in read_ids,
            "is_author": str(item.author_id) == str(reader_user_id) if reader_user_id else False,
            "is_deleted": deletion_map.get(item.id, {}).get("is_deleted", False),
            "deleted_by": deletion_map.get(item.id, {}).get("deleted_by"),
            "author": author_map.get(item.id),
            "author_course_member": author_course_member_map.get(item.id),
        })
        for item in items
    ]


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
    if not cache:
        return

    # Fetch the message to get its target fields
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        return

    # CRITICAL: Invalidate ALL cached views for this user
    # This is necessary because unread message counts appear in course content lists,
    # and those views are cached with complex query parameters and related_ids.
    # The safest approach is to invalidate all views for the user.
    cache.invalidate_user_views(user_id=str(reader_user_id))

    # Additionally, invalidate entity-specific tags for broader cache coherence
    # (in case other users' caches reference these entities)

    if message.submission_group_id:
        # Invalidate submission group entity tags
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
    # Upsert read record for current user
    exists = (
        db.query(MessageRead)
        .filter(MessageRead.message_id == message_id, MessageRead.reader_user_id == permissions.user_id)
        .first()
    )
    if not exists:
        db.add(MessageRead(message_id=message_id, reader_user_id=permissions.user_id))
        db.commit()

        # Invalidate cached views that include unread message counts
        _invalidate_message_cache(message_id, str(permissions.user_id), db, cache)


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


async def list_messages_with_filters(
    permissions: Principal,
    db: Session,
    params: MessageQuery,
) -> Tuple[List[MessageList], int]:
    """List messages with user-specific filtering (unread, tags, datetime).

    This function extends the standard list_entities by passing the current
    user's ID to the search function for unread filtering.

    Args:
        permissions: Current user permissions
        db: Database session
        params: Query parameters including unread, tags, datetime filters

    Returns:
        Tuple of (list of MessageList, total count)
    """
    from computor_backend.interfaces.message import MessageInterface

    # Get permission-filtered base query
    query = check_permissions(permissions, Message, "list", db)

    if query is None:
        return [], 0

    # Apply search filters with reader_user_id for unread filtering
    query = MessageInterface.search(
        db, query, params,
        reader_user_id=str(permissions.user_id) if permissions.user_id else None
    )

    # Execute paginated query in threadpool
    def _get_paginated_results():
        total = query.order_by(None).count()

        paginated_query = query
        if params.limit is not None:
            paginated_query = paginated_query.limit(params.limit)
        if params.skip is not None:
            paginated_query = paginated_query.offset(params.skip)

        results = paginated_query.all()
        return results, total

    results, total = await run_in_threadpool(_get_paginated_results)

    # Convert to MessageList DTOs
    items = [MessageList.model_validate(entity, from_attributes=True) for entity in results]

    return items, total
