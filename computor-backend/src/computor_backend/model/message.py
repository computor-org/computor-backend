from sqlalchemy import (
    BigInteger, Column, DateTime, ForeignKey,
    Index, String, text, Integer
, func)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base


class Message(Base):
    __tablename__ = 'message'
    __table_args__ = (
        Index('msg_parent_archived_idx', 'parent_id', 'archived_at'),
        Index('msg_author_archived_idx', 'author_id', 'archived_at'),
        Index('msg_user_archived_idx', 'user_id', 'archived_at'),
        Index('msg_course_member_archived_idx', 'course_member_id', 'archived_at'),
        Index('msg_submission_group_archived_idx', 'submission_group_id', 'archived_at'),
        Index('msg_course_group_archived_idx', 'course_group_id', 'archived_at'),
        Index('msg_course_content_archived_idx', 'course_content_id', 'archived_at'),
        Index('msg_course_archived_idx', 'course_id', 'archived_at'),
    )

    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    version = Column(BigInteger, server_default=text("0"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by = Column(ForeignKey('user.id', ondelete='SET NULL'))
    updated_by = Column(ForeignKey('user.id', ondelete='SET NULL'))
    properties = Column(JSONB)
    archived_at = Column(DateTime(timezone=True))

    # Author of the message
    author_id = Column(ForeignKey('user.id', ondelete='CASCADE', onupdate='RESTRICT'), nullable=False)

    # Threading
    parent_id = Column(ForeignKey('message.id', ondelete='CASCADE', onupdate='RESTRICT'))
    level = Column(Integer, nullable=False)

    # Content
    title = Column(String(255), nullable=False)
    content = Column(String(16384), nullable=False)

    # Targets (all nullable; at least one may be set; if all course-related are NULL and user_id set, it's a direct user message)
    user_id = Column(ForeignKey('user.id', ondelete='CASCADE', onupdate='RESTRICT'), nullable=True)
    course_member_id = Column(ForeignKey('course_member.id', ondelete='CASCADE', onupdate='RESTRICT'), nullable=True)
    submission_group_id = Column(ForeignKey('submission_group.id', ondelete='CASCADE', onupdate='RESTRICT'), nullable=True)
    course_group_id = Column(ForeignKey('course_group.id', ondelete='CASCADE', onupdate='RESTRICT'), nullable=True)
    course_content_id = Column(ForeignKey('course_content.id', ondelete='CASCADE', onupdate='RESTRICT'), nullable=True)
    course_id = Column(ForeignKey('course.id', ondelete='CASCADE', onupdate='RESTRICT'), nullable=True)

    # Relationships
    author = relationship('User', foreign_keys=[author_id])
    parent = relationship('Message', remote_side=[id], backref='replies')
    created_by_user = relationship('User', foreign_keys=[created_by])
    updated_by_user = relationship('User', foreign_keys=[updated_by])

    user = relationship('User', foreign_keys=[user_id])
    course_member = relationship('CourseMember', foreign_keys=[course_member_id])
    submission_group = relationship('SubmissionGroup', foreign_keys=[submission_group_id])
    course_group = relationship('CourseGroup', foreign_keys=[course_group_id])
    course_content = relationship('CourseContent', foreign_keys=[course_content_id])
    course = relationship('Course', foreign_keys=[course_id])

    message_reads = relationship('MessageRead', back_populates='message', cascade='all, delete-orphan')

    @property
    def is_deleted(self) -> bool:
        """Check if message is soft-deleted."""
        return self.archived_at is not None

    @property
    def deletion_reason(self) -> str:
        """Get deletion reason from properties."""
        if not self.is_deleted or not self.properties:
            return None
        return self.properties.get('deletion_reason')

    @property
    def deleted_by(self) -> str:
        """Get who deleted the message (author/moderator/admin)."""
        if not self.is_deleted or not self.properties:
            return 'author'
        return self.properties.get('deleted_by', 'author')


class MessageRead(Base):
    __tablename__ = 'message_read'
    __table_args__ = (
        Index('msg_read_unique_idx', 'message_id', 'reader_user_id', unique=True),
    )

    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    version = Column(BigInteger, server_default=text("0"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by = Column(ForeignKey('user.id', ondelete='SET NULL'))
    updated_by = Column(ForeignKey('user.id', ondelete='SET NULL'))
    properties = Column(JSONB)

    message_id = Column(ForeignKey('message.id', ondelete='CASCADE', onupdate='RESTRICT'), nullable=False)
    reader_user_id = Column(ForeignKey('user.id', ondelete='CASCADE', onupdate='RESTRICT'), nullable=False)

    # Relationships
    message = relationship('Message', back_populates='message_reads')
    reader_user = relationship('User', foreign_keys=[reader_user_id])
    created_by_user = relationship('User', foreign_keys=[created_by])
    updated_by_user = relationship('User', foreign_keys=[updated_by])
