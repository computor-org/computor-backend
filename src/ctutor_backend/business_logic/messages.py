"""Business logic for message operations."""
from uuid import UUID
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from ctutor_backend.api.exceptions import BadRequestException
from ctutor_backend.permissions.principal import Principal
from ctutor_backend.model.message import MessageRead
from ctutor_backend.interface.messages import MessageCreate, MessageGet


def create_message_with_author(
    payload: MessageCreate,
    permissions: Principal,
    db: Session,
) -> dict:
    """Create a message with enforced author_id and defaults.

    Args:
        payload: Message creation data
        permissions: Current user permissions
        db: Database session

    Returns:
        Dictionary with model_dump ready for create_db

    Raises:
        BadRequestException: If title or content missing
    """
    # Enforce author_id from current user
    if not payload.title or not payload.content:
        raise BadRequestException(detail="Title and content are required")

    model_dump = payload.model_dump(exclude_unset=True)
    model_dump['author_id'] = permissions.user_id

    # At least one target is recommended (user_id, course_member_id, submission_group_id, course_group_id)
    if not any(model_dump.get(k) for k in ['user_id', 'course_member_id', 'submission_group_id', 'course_group_id', 'course_content_id', 'course_id']):
        # Allow user-only message by setting user_id to current user if nothing else provided
        model_dump['user_id'] = permissions.user_id

    # Default level
    if 'level' not in model_dump or model_dump['level'] is None:
        model_dump['level'] = 0

    return model_dump


def get_message_with_read_status(
    message_id: UUID | str,
    message: MessageGet,
    permissions: Principal,
    db: Session,
) -> MessageGet:
    """Get a message with read status for current user.

    Args:
        message_id: Message ID
        message: Message entity from get_id_db
        permissions: Current user permissions
        db: Database session

    Returns:
        Message with is_read field populated
    """
    reader_user_id = permissions.user_id
    is_read = False
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

    return message.model_copy(update={"is_read": is_read})


def list_messages_with_read_status(
    items: list[MessageGet],
    permissions: Principal,
    db: Session,
) -> list[MessageGet]:
    """Add read status to a list of messages for current user.

    Args:
        items: List of messages
        permissions: Current user permissions
        db: Database session

    Returns:
        List of messages with is_read field populated
    """
    reader_user_id = permissions.user_id

    if reader_user_id and items:
        message_ids = [item.id for item in items]
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

    return [item.model_copy(update={"is_read": item.id in read_ids}) for item in items]


def mark_message_as_read(
    message_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> None:
    """Mark a message as read for the current user.

    Args:
        message_id: Message ID
        permissions: Current user permissions
        db: Database session
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


def mark_message_as_unread(
    message_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> None:
    """Mark a message as unread for the current user.

    Args:
        message_id: Message ID
        permissions: Current user permissions
        db: Database session
    """
    read = (
        db.query(MessageRead)
        .filter(MessageRead.message_id == message_id, MessageRead.reader_user_id == permissions.user_id)
        .first()
    )
    if read:
        db.delete(read)
        db.commit()
