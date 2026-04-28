"""Business logic for message operations."""
from uuid import UUID
from typing import Optional, Tuple, List, Dict, Any
from sqlalchemy.orm import Session

from computor_backend.api.exceptions import BadRequestException, NotImplementedException, ForbiddenException
from computor_backend.permissions.principal import Principal
from computor_backend.permissions.core import check_permissions
from computor_backend.model.message import MessageRead, Message
from computor_backend.model.course import (
    Course,
    CourseContent,
    CourseFamilyMember,
    CourseGroup,
    CourseMember,
    SubmissionGroup,
    SubmissionGroupMember,
)
from computor_backend.model.organization import OrganizationMember
from computor_backend.model.role import UserRole
from computor_backend.model.auth import User


# Most-specific to least-specific. Mirrors the hierarchy comment on
# ``model.message.Message`` and powers single-target enforcement on create.
MESSAGE_TARGET_FIELDS = (
    'user_id',
    'course_member_id',
    'submission_group_id',
    'course_content_id',
    'course_group_id',
    'course_id',
    'course_family_id',
    'organization_id',
)
from computor_types.messages import (
    MessageCreate, MessageGet, MessageList, MessageQuery,
    MessageAuthor, MessageAuthorCourseMember, MessageThread
)
from computor_backend.cache import Cache


def create_message_with_author(
    payload: MessageCreate,
    permissions: Principal,
    db: Session,
) -> dict:
    """Create a message with enforced author_id and scope-based permission checks.

    Single-target rule: each message has exactly one target column set; every
    other target column is explicitly nulled out before persistence. This is
    what keeps the read filter in ``MessagePermissionHandler`` honest —
    visibility per target type cannot leak across scopes (e.g. a
    submission-group message must not become readable to all course members
    just because the create path also stamped ``course_id``).

    Replies inherit their parent's target so a thread always lives in one
    scope.

    Write rules per primary target (read rules live in
    ``MessagePermissionHandler.build_query``):

    +-----------------------+--------------------------------------------------+
    | None (global)         | admin only on write; everyone can read           |
    | user_id               | direct chat — implemented but currently disabled |
    |                       | (raises NotImplementedException)                 |
    | course_member_id      | not implemented yet (raises NotImplementedException) |
    | submission_group_id   | submission_group_member OR course role >= _tutor |
    | course_content_id     | course role >= _lecturer                         |
    | course_group_id       | course role >= _lecturer                         |
    | course_id             | course role >= _lecturer                         |
    | course_family_id      | scoped course_family role >= _manager (admin OK) |
    | organization_id       | scoped organization role >= _manager (admin OK)  |
    +-----------------------+--------------------------------------------------+

    Raises:
        BadRequestException: If content missing or reply scope mismatch.
        NotImplementedException: For not-yet-enabled targets (user_id,
            course_member_id).
        ForbiddenException: If the principal lacks the role required for
            the target's scope.
    """
    if not payload.content:
        raise BadRequestException(detail="Content is required")

    model_dump = payload.model_dump(exclude_unset=True)
    model_dump['author_id'] = permissions.user_id

    if model_dump.get('parent_id'):
        parent_message = db.query(Message).filter(Message.id == model_dump['parent_id']).first()
        if not parent_message:
            raise BadRequestException(detail=f"Parent message {model_dump['parent_id']} not found")

        # If the client set a target, it must match the parent's same field.
        for field in MESSAGE_TARGET_FIELDS:
            client_value = model_dump.get(field)
            parent_value = getattr(parent_message, field, None)
            if client_value and parent_value and str(client_value) != str(parent_value):
                raise BadRequestException(
                    detail=f"Reply scope mismatch: {field} must match the parent message "
                           f"(expected {parent_value}, got {client_value})"
                )

        # Inherit any target the client didn't specify.
        for field in MESSAGE_TARGET_FIELDS:
            parent_value = getattr(parent_message, field, None)
            if parent_value is not None and not model_dump.get(field):
                model_dump[field] = parent_value

    # Most-specific set field wins; everything else is nulled.
    primary_target = next((f for f in MESSAGE_TARGET_FIELDS if model_dump.get(f)), None)
    for field in MESSAGE_TARGET_FIELDS:
        if field != primary_target:
            model_dump[field] = None

    if primary_target is None:
        _check_global_write_permission(permissions)
    elif primary_target == 'user_id':
        _check_user_message_write_permission(permissions, model_dump['user_id'], db)
    elif primary_target == 'course_member_id':
        raise NotImplementedException(
            detail="Course member messages (course_member_id target) are not implemented yet"
        )
    elif primary_target == 'submission_group_id':
        _check_submission_group_write_permission(permissions, model_dump['submission_group_id'], db)
    elif primary_target == 'course_content_id':
        _check_course_content_write_permission(permissions, model_dump['course_content_id'], db)
    elif primary_target == 'course_group_id':
        _check_course_group_write_permission(permissions, model_dump['course_group_id'], db)
    elif primary_target == 'course_id':
        _check_course_write_permission(permissions, model_dump['course_id'], db)
    elif primary_target == 'course_family_id':
        _check_course_family_write_permission(permissions, model_dump['course_family_id'])
    elif primary_target == 'organization_id':
        _check_organization_write_permission(permissions, model_dump['organization_id'])

    if 'level' not in model_dump or model_dump['level'] is None:
        model_dump['level'] = 0

    return model_dump


def _check_global_write_permission(permissions: Principal) -> None:
    """Global messages (no target set) are admin-only."""
    if not getattr(permissions, 'is_admin', False):
        raise ForbiddenException(
            detail="Only administrators can create global messages"
        )


def _check_user_message_write_permission(
    permissions: Principal,
    user_id: str,
    db: Session,
) -> None:
    """Direct user-to-user message (one-on-one chat).

    The handler path is wired end-to-end (visibility, audit, broadcast)
    but creation is intentionally disabled until the product side
    settles on rate-limiting / abuse handling. To enable: drop the raise
    below — the rest of the path is already correct.

    Intended rules when enabled:
    - recipient must exist
    - author must not message themselves
    - no role required (this is a direct chat)
    """
    raise NotImplementedException(
        detail="Direct user-to-user messages are not implemented yet"
    )


def _check_organization_write_permission(
    permissions: Principal,
    organization_id: str,
) -> None:
    """Organization messages: scoped role >= _manager (admin bypass).

    ``_developer`` is intentionally excluded — org-level announcements are
    a higher-trust action than ordinary org administration.
    """
    if not permissions.has_organization_role(organization_id, "_manager"):
        raise ForbiddenException(
            detail="Requires organization _manager or _owner role to post organization messages"
        )


def _check_course_family_write_permission(
    permissions: Principal,
    course_family_id: str,
) -> None:
    """Course-family messages: scoped role >= _manager (admin bypass)."""
    if not permissions.has_course_family_role(course_family_id, "_manager"):
        raise ForbiddenException(
            detail="Requires course_family _manager or _owner role to post course family messages"
        )


def _check_course_group_write_permission(
    permissions: Principal,
    course_group_id: str,
    db: Session,
) -> None:
    """Course-group messages: course role >= _lecturer in the group's course."""
    course_group = db.query(CourseGroup).filter(CourseGroup.id == course_group_id).first()
    if not course_group:
        raise ForbiddenException(detail="Course group not found")

    has_lecturer_role = db.query(
        db.query(CourseMember.id)
        .filter(
            CourseMember.course_id == course_group.course_id,
            CourseMember.user_id == permissions.user_id,
            CourseMember.course_role_id.in_(["_lecturer", "_maintainer", "_owner"]),
        )
        .exists()
    ).scalar()

    if not has_lecturer_role:
        raise ForbiddenException()


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


_ELEVATED_COURSE_ROLES = ("_tutor", "_lecturer", "_maintainer", "_owner")


def get_message_recipient_user_ids(message: Message, db: Session) -> set[str]:
    """Compute the set of user_ids that have read access to ``message``.

    Inverse of ``MessagePermissionHandler.build_query`` — given a stored
    Message row, return everyone who can see it. Used by the WS broadcast
    layer to fan messages out to per-user inbox channels (``user:<id>``).

    Single-target invariant: each message has at most one target column
    set, so the per-scope branches below are mutually exclusive.

    Returns an empty set for global messages (no targets) — the broadcast
    layer publishes those to the dedicated ``global`` channel, which every
    connected client is auto-subscribed to.

    Always includes:
    - the author (so they see their own posts on their inbox)
    - every system admin (admins bypass scope checks; their inbox should
      reflect everything)
    """
    user_ids: set[str] = set()

    if message.author_id:
        user_ids.add(str(message.author_id))

    admin_rows = db.query(UserRole.user_id).filter(UserRole.role_id == "_admin").all()
    user_ids.update(str(r[0]) for r in admin_rows)

    if message.user_id:
        user_ids.add(str(message.user_id))
        return user_ids

    if message.course_member_id:
        cm = db.query(CourseMember).filter(CourseMember.id == message.course_member_id).first()
        if cm:
            user_ids.add(str(cm.user_id))
            user_ids.update(_elevated_user_ids(db, cm.course_id))
        return user_ids

    if message.submission_group_id:
        sg = db.query(SubmissionGroup).filter(
            SubmissionGroup.id == message.submission_group_id
        ).first()
        if sg:
            member_rows = (
                db.query(CourseMember.user_id)
                .join(
                    SubmissionGroupMember,
                    SubmissionGroupMember.course_member_id == CourseMember.id,
                )
                .filter(SubmissionGroupMember.submission_group_id == sg.id)
                .all()
            )
            user_ids.update(str(r[0]) for r in member_rows)
            user_ids.update(_elevated_user_ids(db, sg.course_id))
        return user_ids

    if message.course_group_id:
        cg = db.query(CourseGroup).filter(CourseGroup.id == message.course_group_id).first()
        if cg:
            member_rows = (
                db.query(CourseMember.user_id)
                .filter(CourseMember.course_group_id == cg.id)
                .all()
            )
            user_ids.update(str(r[0]) for r in member_rows)
            user_ids.update(_elevated_user_ids(db, cg.course_id))
        return user_ids

    if message.course_content_id:
        cc = db.query(CourseContent).filter(
            CourseContent.id == message.course_content_id
        ).first()
        if cc:
            member_rows = (
                db.query(CourseMember.user_id)
                .filter(CourseMember.course_id == cc.course_id)
                .all()
            )
            user_ids.update(str(r[0]) for r in member_rows)
        return user_ids

    if message.course_id:
        member_rows = (
            db.query(CourseMember.user_id)
            .filter(CourseMember.course_id == message.course_id)
            .all()
        )
        user_ids.update(str(r[0]) for r in member_rows)
        return user_ids

    if message.course_family_id:
        member_rows = (
            db.query(CourseMember.user_id)
            .join(Course, Course.id == CourseMember.course_id)
            .filter(Course.course_family_id == message.course_family_id)
            .all()
        )
        user_ids.update(str(r[0]) for r in member_rows)
        scoped_rows = (
            db.query(CourseFamilyMember.user_id)
            .filter(CourseFamilyMember.course_family_id == message.course_family_id)
            .all()
        )
        user_ids.update(str(r[0]) for r in scoped_rows)
        return user_ids

    if message.organization_id:
        member_rows = (
            db.query(CourseMember.user_id)
            .join(Course, Course.id == CourseMember.course_id)
            .filter(Course.organization_id == message.organization_id)
            .all()
        )
        user_ids.update(str(r[0]) for r in member_rows)
        scoped_rows = (
            db.query(OrganizationMember.user_id)
            .filter(OrganizationMember.organization_id == message.organization_id)
            .all()
        )
        user_ids.update(str(r[0]) for r in scoped_rows)
        return user_ids

    # Global — recipient set is "everyone connected", which the broadcast
    # layer handles via the dedicated ``global`` channel. Returning an
    # empty set here avoids fanning out N-thousand publishes per message.
    return set()


def _elevated_user_ids(db: Session, course_id) -> set[str]:
    """User IDs holding ``_tutor`` or higher in ``course_id``."""
    rows = (
        db.query(CourseMember.user_id)
        .filter(
            CourseMember.course_id == course_id,
            CourseMember.course_role_id.in_(_ELEVATED_COURSE_ROLES),
        )
        .all()
    )
    return {str(r[0]) for r in rows}


def invalidate_tutor_lecturer_views_for_message(
    message: Message,
    db: Session,
    cache: Optional[Cache] = None,
) -> None:
    """
    Clear cached tutor and lecturer course views affected by a message create/delete.

    Every tutor's `unread_message_count` badge for a course member depends on the
    set of non-archived messages scoped to that member's submission group. When a
    new message is posted (or soft-deleted), that set changes, so every tutor's
    cached view for the course must be invalidated.

    Resolves the effective course_id via the message's scope hierarchy when
    `message.course_id` itself is NULL (submission-group-scoped messages):
        submission_group.course_id -> course_content.course_id

    Note: this is a no-op for read/unread state changes — those are per-user and
    are handled by `_invalidate_message_cache`.
    """
    if cache is None or message is None:
        return

    course_id = message.course_id

    if course_id is None and message.submission_group_id:
        course_id = db.query(SubmissionGroup.course_id).filter(
            SubmissionGroup.id == message.submission_group_id
        ).scalar()

    if course_id is None and message.course_content_id:
        course_id = db.query(CourseContent.course_id).filter(
            CourseContent.id == message.course_content_id
        ).scalar()

    if course_id is None:
        return

    cache.invalidate_tags(f"tutor_view:{course_id}")
    cache.invalidate_tags(f"lecturer_view:{course_id}")


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


def list_messages_with_filters(
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

    total = query.order_by(None).count()

    paginated_query = query
    if params.limit is not None:
        paginated_query = paginated_query.limit(params.limit)
    if params.skip is not None:
        paginated_query = paginated_query.offset(params.skip)

    results = paginated_query.all()

    # Convert to MessageList DTOs
    items = [MessageList.model_validate(entity, from_attributes=True) for entity in results]

    return items, total


def get_message_thread(
    message_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> MessageThread:
    """Get the full conversation thread for a message.

    Walks up the parent chain to find the root message, then fetches
    all descendants of that root. Returns all messages ordered by created_at.

    Args:
        message_id: Any message ID in the thread
        permissions: Current user permissions
        db: Database session

    Returns:
        MessageThread with root_message_id and all messages in order

    Raises:
        BadRequestException: If message not found
    """
    # Walk up to root
    start_message = db.query(Message).filter(
        Message.id == message_id,
        Message.archived_at.is_(None),
    ).first()

    if not start_message:
        raise BadRequestException(detail=f"Message {message_id} not found")

    # Walk up the parent chain to find the root
    root = start_message
    while root.parent_id is not None:
        parent = db.query(Message).filter(Message.id == root.parent_id).first()
        if parent is None:
            break
        root = parent

    root_id = str(root.id)

    # Use recursive CTE to get all descendants of the root
    # This is efficient and handles arbitrary nesting depth
    cte = (
        db.query(Message.id)
        .filter(Message.id == root_id)
        .cte(name="thread", recursive=True)
    )
    cte = cte.union_all(
        db.query(Message.id)
        .filter(Message.parent_id == cte.c.id)
    )

    # Fetch all thread messages, ordered chronologically
    thread_messages = (
        db.query(Message)
        .filter(Message.id.in_(db.query(cte.c.id)))
        .filter(Message.archived_at.is_(None))
        .order_by(Message.created_at.asc())
        .all()
    )

    # Enrich with read status and author info
    items = [MessageList.model_validate(msg, from_attributes=True) for msg in thread_messages]
    enriched = list_messages_with_read_status(items, permissions, db)

    return MessageThread(
        root_message_id=root_id,
        messages=enriched,
        total=len(enriched),
    )
