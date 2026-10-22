from typing import Optional

from sqlalchemy import (
    BigInteger, CheckConstraint, Column, DateTime, ForeignKey,
    Index, String, Text, text, Integer
, func)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base, UUIDPkMixin, VersionedMixin, AuditMixin


class Message(UUIDPkMixin, VersionedMixin, AuditMixin, Base):
    __tablename__ = 'message'
    __table_args__ = (
        Index('msg_parent_archived_idx', 'parent_id', 'archived_at'),
        Index('msg_author_archived_idx', 'author_id', 'archived_at'),
        Index('msg_organization_archived_idx', 'organization_id', 'archived_at'),
        Index('msg_course_family_archived_idx', 'course_family_id', 'archived_at'),
        Index('msg_course_archived_idx', 'course_id', 'archived_at'),
        Index('msg_course_content_archived_idx', 'course_content_id', 'archived_at'),
        Index('msg_course_group_archived_idx', 'course_group_id', 'archived_at'),
        Index('msg_submission_group_archived_idx', 'submission_group_id', 'archived_at'),
        Index('msg_course_member_archived_idx', 'course_member_id', 'archived_at'),
        Index('msg_user_archived_idx', 'user_id', 'archived_at'),
        Index('msg_ticket_created_idx', 'ticket_id', 'created_at'),
        CheckConstraint(
            "visibility IN ('public', 'internal')", name='msg_visibility_check'
        ),
        # Only ticket messages may lack an author (mail from outside), and
        # only ticket messages may be internal.
        CheckConstraint(
            "author_id IS NOT NULL OR ticket_id IS NOT NULL", name='msg_author_or_ticket_check'
        ),
        CheckConstraint(
            "visibility = 'public' OR ticket_id IS NOT NULL", name='msg_internal_ticket_only_check'
        ),
        # Ticket messages never carry a course/user scope target or a parent,
        # so no course-messaging read path (scope filters, thread walks,
        # unread counters) can reach them.
        CheckConstraint(
            "ticket_id IS NULL OR (parent_id IS NULL AND organization_id IS NULL"
            " AND course_family_id IS NULL AND course_id IS NULL"
            " AND course_content_id IS NULL AND course_group_id IS NULL"
            " AND submission_group_id IS NULL AND course_member_id IS NULL"
            " AND user_id IS NULL)",
            name='msg_ticket_unscoped_check',
        ),
    )

    properties = Column(JSONB)
    archived_at = Column(DateTime(timezone=True))

    # Author of the message. NULL only for ticket messages that came in by
    # mail from outside (the sender is in ``properties['mail']``).
    author_id = Column(ForeignKey('user.id', ondelete='CASCADE', onupdate='RESTRICT'), nullable=True)

    # Support tickets (issues#520). A message with a ticket is served only by
    # the /support endpoints; MessagePermissionHandler excludes it everywhere
    # else. ``internal`` messages are team notes the reporter never sees.
    ticket_id = Column(ForeignKey('ticket.id', ondelete='CASCADE', onupdate='RESTRICT'), nullable=True)
    visibility = Column(String(16), nullable=False, server_default=text("'public'"))

    # Threading
    parent_id = Column(ForeignKey('message.id', ondelete='CASCADE', onupdate='RESTRICT'))
    level = Column(Integer, nullable=False)

    # Content
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)

    # Targets (all nullable; if ALL are NULL = global message visible to all users)
    # Hierarchy: organization > course_family > course > course_content/course_group > submission_group > course_member > user
    organization_id = Column(ForeignKey('organization.id', ondelete='CASCADE', onupdate='RESTRICT'), nullable=True)
    course_family_id = Column(ForeignKey('course_family.id', ondelete='CASCADE', onupdate='RESTRICT'), nullable=True)
    course_id = Column(ForeignKey('course.id', ondelete='CASCADE', onupdate='RESTRICT'), nullable=True)
    course_content_id = Column(ForeignKey('course_content.id', ondelete='CASCADE', onupdate='RESTRICT'), nullable=True)
    course_group_id = Column(ForeignKey('course_group.id', ondelete='CASCADE', onupdate='RESTRICT'), nullable=True)
    submission_group_id = Column(ForeignKey('submission_group.id', ondelete='CASCADE', onupdate='RESTRICT'), nullable=True)
    course_member_id = Column(ForeignKey('course_member.id', ondelete='CASCADE', onupdate='RESTRICT'), nullable=True)
    user_id = Column(ForeignKey('user.id', ondelete='CASCADE', onupdate='RESTRICT'), nullable=True)

    # Relationships
    author = relationship('User', foreign_keys=[author_id])
    parent = relationship('Message', remote_side="Message.id", backref='replies')

    organization = relationship('Organization', foreign_keys=[organization_id])
    course_family = relationship('CourseFamily', foreign_keys=[course_family_id])
    course = relationship('Course', foreign_keys=[course_id])
    course_content = relationship('CourseContent', foreign_keys=[course_content_id])
    course_group = relationship('CourseGroup', foreign_keys=[course_group_id])
    submission_group = relationship('SubmissionGroup', foreign_keys=[submission_group_id])
    course_member = relationship('CourseMember', foreign_keys=[course_member_id])
    user = relationship('User', foreign_keys=[user_id])
    ticket = relationship('Ticket', back_populates='messages')

    message_reads = relationship('MessageRead', back_populates='message', cascade='all, delete-orphan')
    mentions = relationship('MessageMention', back_populates='message', cascade='all, delete-orphan')

    @property
    def is_deleted(self) -> bool:
        """Check if message is soft-deleted."""
        return self.archived_at is not None

    @property
    def deletion_reason(self) -> Optional[str]:
        """Get deletion reason from properties."""
        if not self.is_deleted or not self.properties:
            return None
        return self.properties.get('deletion_reason')

    @property
    def deleted_by(self) -> Optional[str]:
        """Get who deleted the message (author/moderator/admin).

        None for a message that is still live — it has no deleter, and
        claiming 'author' made every message look deleted to any client that
        read this field without checking ``is_deleted`` first.
        """
        if not self.is_deleted:
            return None
        if not self.properties:
            return 'author'
        return self.properties.get('deleted_by', 'author')


class MessageRead(UUIDPkMixin, VersionedMixin, AuditMixin, Base):
    __tablename__ = 'message_read'
    __table_args__ = (
        Index('msg_read_unique_idx', 'message_id', 'reader_user_id', unique=True),
    )

    properties = Column(JSONB)

    message_id = Column(ForeignKey('message.id', ondelete='CASCADE', onupdate='RESTRICT'), nullable=False)
    reader_user_id = Column(ForeignKey('user.id', ondelete='CASCADE', onupdate='RESTRICT'), nullable=False)

    # Relationships
    message = relationship('Message', back_populates='message_reads')
    reader_user = relationship('User', foreign_keys=[reader_user_id])


class MessageMention(Base):
    """A user mentioned in a message.

    Created from the ``@[name](user_id)`` tokens in ``Message.content`` once the
    mentioned user is confirmed to be in the message's audience. Powers fast
    "messages that mention me" lookups and AI-agent activation. Intentionally
    lean (no audit columns / trigger): the message author is the implicit
    creator and rows are derived from content.
    """
    __tablename__ = 'message_mention'
    __table_args__ = (
        Index('msg_mention_unique_idx', 'message_id', 'mentioned_user_id', unique=True),
        Index('msg_mention_user_idx', 'mentioned_user_id', 'message_id'),
    )

    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    message_id = Column(ForeignKey('message.id', ondelete='CASCADE', onupdate='RESTRICT'), nullable=False)
    mentioned_user_id = Column(ForeignKey('user.id', ondelete='CASCADE', onupdate='RESTRICT'), nullable=False)

    # Relationships
    message = relationship('Message', back_populates='mentions')
    mentioned_user = relationship('User', foreign_keys=[mentioned_user_id])
