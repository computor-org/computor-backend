"""Message creation (single-target + scope permission enforcement),
user-filtered listing and thread assembly."""
from uuid import UUID
from typing import Tuple, List
from sqlalchemy.orm import Session

from computor_backend.exceptions import BadRequestException, NotImplementedException
from computor_backend.permissions.principal import Principal
from computor_backend.permissions.core import check_permissions
from computor_backend.model.message import Message
from computor_types.messages import (
    MessageCreate, MessageQuery, MessageList, MessageThread,
)
from .permissions import (
    _check_global_write_permission,
    _check_user_message_write_permission,
    _check_submission_group_write_permission,
    _check_course_content_write_permission,
    _check_course_group_write_permission,
    _check_course_write_permission,
    _check_course_family_write_permission,
    _check_organization_write_permission,
)
from .mentions import validate_message_mentions, _transient_message_for_targets
from .read_status import list_messages_with_read_status


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


# Scopes that support back-and-forth conversations (i.e. ``parent_id``
# replies are meaningful). Everything else is broadcast / announcement
# territory: a student replying to a course-wide announcement would
# otherwise have their reply fan out to every course member, which is
# the opposite of what announcements are for.
CONVERSATIONAL_TARGET_FIELDS = frozenset({
    'user_id',
    'course_member_id',
    'submission_group_id',
})


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

    # Replies are only meaningful on conversational scopes. Allowing a
    # reply on e.g. ``course_id`` would fan a student's reply out to
    # every course member — that's the opposite of what an announcement
    # scope is for. Mirrors the client-side reply policy shipped in the
    # vscode extension.
    if model_dump.get('parent_id') and primary_target not in CONVERSATIONAL_TARGET_FIELDS:
        scope_label = primary_target or 'global'
        raise BadRequestException(
            detail=(
                f"Replies are not allowed on {scope_label} messages — "
                "those scopes are announcement-only. Conversational "
                "scopes are: user, course_member, submission_group."
            )
        )

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

    # Gate @mentions against the message's audience before persistence — you
    # cannot mention a user who could not see the message. The relation rows
    # are written post-persist via ``sync_message_mentions`` (the message
    # needs an id first).
    validate_message_mentions(
        _transient_message_for_targets(model_dump, permissions.user_id),
        model_dump.get('content'),
        db,
    )

    return model_dump


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
        raise BadRequestException(
            detail="Message not found",
            context={"message_id": str(message_id)},
        )

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
