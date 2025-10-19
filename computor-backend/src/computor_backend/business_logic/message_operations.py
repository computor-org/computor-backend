"""Business logic for message operations with audit logging."""
from datetime import datetime, timezone
from uuid import UUID
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from computor_backend.model.message import Message
from computor_backend.model.message_audit import MessageAuditLog, MessageAuditAction
from computor_backend.permissions.principal import Principal
from computor_backend.api.exceptions import ForbiddenException, NotFoundException


def soft_delete_message(
    message_id: UUID | str,
    principal: Principal,
    db: Session,
    reason: str = "user_request"
) -> Message:
    """Soft delete a message by setting archived_at.

    Instead of deleting the message, we mark it as archived and replace
    the content with a deletion notice. This preserves the thread structure
    for replies.

    Args:
        message_id: Message to delete
        principal: Current user
        db: Database session
        reason: Deletion reason for audit

    Returns:
        The archived message

    Raises:
        NotFoundException: If message not found
        ForbiddenException: If user not authorized
    """
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise NotFoundException(
            error_code="NF_001",
            detail=f"Message {message_id} not found"
        )

    # Check if user is author or admin
    is_author = str(message.author_id) == str(principal.user_id)
    is_admin = getattr(principal, 'is_admin', False)

    if not is_author and not is_admin:
        raise ForbiddenException(
            error_code="AUTHZ_001",
            detail="Only the author or admin can delete messages"
        )

    # Already deleted?
    if message.is_deleted:
        return message

    # Store original content for audit
    old_title = message.title
    old_content = message.content

    # Soft delete - set archived_at and update properties
    message.archived_at = datetime.now(timezone.utc)
    message.properties = message.properties or {}
    message.properties['deletion_reason'] = reason
    message.properties['deleted_by'] = 'author' if is_author else ('admin' if is_admin else 'moderator')
    message.properties['deleted_at'] = datetime.now(timezone.utc).isoformat()

    # IMPORTANT: Mark properties as modified for JSONB tracking
    flag_modified(message, 'properties')

    # Replace title and content with deletion notice
    deleted_by_text = message.properties['deleted_by']
    message.title = f"[Message deleted by {deleted_by_text}]"
    message.content = f"[This message was deleted by the {deleted_by_text}]"
    message.updated_at = datetime.now(timezone.utc)
    message.updated_by = str(principal.user_id)

    # Create audit log entry
    audit = MessageAuditLog(
        message_id=message.id,
        user_id=principal.user_id,
        action=MessageAuditAction.DELETED,
        old_title=old_title,
        old_content=old_content,
        new_title=message.title,
        new_content=message.content
    )
    db.add(audit)
    db.commit()
    db.refresh(message)

    return message


def update_message_with_audit(
    message_id: UUID | str,
    principal: Principal,
    db: Session,
    new_title: Optional[str] = None,
    new_content: Optional[str] = None
) -> Message:
    """Update a message and create audit log.

    Args:
        message_id: Message to update
        principal: Current user
        db: Database session
        new_title: New title (optional)
        new_content: New content (optional)

    Returns:
        Updated message

    Raises:
        NotFoundException: If message not found
        ForbiddenException: If user not authorized or message deleted
    """
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise NotFoundException(
            error_code="NF_001",
            detail=f"Message {message_id} not found"
        )

    # Check if user is author
    if str(message.author_id) != str(principal.user_id):
        raise ForbiddenException(
            error_code="AUTHZ_001",
            detail="Only the author can update messages"
        )

    # Can't update deleted messages
    if message.is_deleted:
        raise ForbiddenException(
            error_code="AUTHZ_001",
            detail="Cannot update deleted messages"
        )

    # Store old values
    old_title = message.title
    old_content = message.content

    # Track what changed
    fields_changed = []
    if new_title is not None and new_title != old_title:
        message.title = new_title
        fields_changed.append("title")

    if new_content is not None and new_content != old_content:
        message.content = new_content
        fields_changed.append("content")

    # Only create audit if something changed
    if fields_changed:
        message.updated_at = datetime.now(timezone.utc)

        audit = MessageAuditLog(
            message_id=message.id,
            user_id=principal.user_id,
            action=MessageAuditAction.UPDATED,
            old_title=old_title if "title" in fields_changed else None,
            old_content=old_content if "content" in fields_changed else None,
            new_title=message.title if "title" in fields_changed else None,
            new_content=message.content if "content" in fields_changed else None
        )
        db.add(audit)
        db.commit()
        db.refresh(message)

    return message


def create_message_audit(
    message: Message,
    principal: Principal,
    db: Session
) -> MessageAuditLog:
    """Create audit log entry for message creation.

    Args:
        message: Newly created message
        principal: Current user
        db: Database session

    Returns:
        The created audit log entry
    """
    audit = MessageAuditLog(
        message_id=message.id,
        user_id=principal.user_id,
        action=MessageAuditAction.CREATED,
        new_title=message.title,
        new_content=message.content
    )
    db.add(audit)
    db.commit()

    return audit


def get_message_audit_history(
    message_id: UUID | str,
    principal: Principal,
    db: Session
) -> list[MessageAuditLog]:
    """Get audit history for a message.

    Only the message author or admin can view the audit history.

    Args:
        message_id: Message ID
        principal: Current user
        db: Database session

    Returns:
        List of audit log entries, newest first

    Raises:
        NotFoundException: If message not found
        ForbiddenException: If user not authorized
    """
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise NotFoundException(
            error_code="NF_001",
            detail=f"Message {message_id} not found"
        )

    # Check if user is author or admin
    is_author = str(message.author_id) == str(principal.user_id)
    is_admin = getattr(principal, 'is_admin', False)

    if not is_author and not is_admin:
        raise ForbiddenException(
            error_code="AUTHZ_001",
            detail="Only the message author or admin can view audit history"
        )

    # Get audit logs
    logs = (
        db.query(MessageAuditLog)
        .filter(MessageAuditLog.message_id == message_id)
        .order_by(MessageAuditLog.created_at.desc())
        .all()
    )

    return logs
