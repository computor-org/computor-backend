from sqlalchemy import (
    BigInteger, Column, DateTime, ForeignKey,
    Index, String, text, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from .base import Base


class MessageAuditAction(str, enum.Enum):
    """Message audit action types."""
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    RESTORED = "restored"  # If we want to support undelete


class MessageAuditLog(Base):
    """Audit log for message changes.

    Tracks all create, update, and delete operations on messages
    to provide a complete history of changes.
    """
    __tablename__ = 'message_audit_log'
    __table_args__ = (
        Index('msg_audit_message_idx', 'message_id', 'created_at'),
        Index('msg_audit_user_idx', 'user_id', 'created_at'),
        Index('msg_audit_action_idx', 'action', 'created_at'),
    )

    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    # What message was changed
    message_id = Column(ForeignKey('message.id', ondelete='CASCADE'), nullable=False)

    # Who made the change
    user_id = Column(ForeignKey('user.id', ondelete='SET NULL'))

    # What action was performed
    action = Column(SQLEnum(MessageAuditAction), nullable=False)

    # Previous values (for updates and deletes)
    old_title = Column(String(255))
    old_content = Column(String(16384))

    # New values (for updates)
    new_title = Column(String(255))
    new_content = Column(String(16384))

    # Relationships
    message = relationship('Message', backref='audit_logs')
    user = relationship('User')
