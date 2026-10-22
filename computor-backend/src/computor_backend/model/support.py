"""Support tickets: team mail and problem reports (computor-org/issues#520).

A ticket's conversation lives in ordinary ``message`` rows carrying
``ticket_id`` (see ``model/message.py``). Those rows never carry a course or
user target, so the course-messaging read paths cannot reach them; the
permission handler additionally excludes every row with a ticket.

``ticket_mail_message`` maps RFC 5322 Message-IDs to tickets. Its unique
index makes the mail import idempotent per Message-ID and is what threading by
In-Reply-To / References looks up.
"""

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Sequence,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import AuditMixin, Base, UUIDPkMixin, VersionedMixin

TICKET_STATUSES = ("open", "in_progress", "waiting", "done")
TICKET_CHANNELS = ("mail", "web", "vscode")
TICKET_PRIORITIES = ("low", "normal", "high")

ticket_number_seq = Sequence("ticket_number_seq")


class Ticket(UUIDPkMixin, VersionedMixin, AuditMixin, Base):
    __tablename__ = "ticket"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'in_progress', 'waiting', 'done')", name="ticket_status_check"
        ),
        CheckConstraint("channel IN ('mail', 'web', 'vscode')", name="ticket_channel_check"),
        CheckConstraint("priority IN ('low', 'normal', 'high')", name="ticket_priority_check"),
        Index("ticket_status_idx", "status", "last_message_at"),
        Index("ticket_assignee_idx", "assignee_id", "status"),
    )

    number = Column(
        BigInteger,
        ticket_number_seq,
        server_default=ticket_number_seq.next_value(),
        nullable=False,
        unique=True,
    )
    subject = Column(String(998), nullable=False)
    channel = Column(String(16), nullable=False, server_default=text("'mail'"))
    status = Column(String(16), nullable=False, server_default=text("'open'"))
    priority = Column(String(16), nullable=False, server_default=text("'normal'"))
    # Restricted tickets (e.g. to security@) are visible to _admin only.
    restricted = Column(Boolean, nullable=False, server_default=text("false"))
    # Team address the first mail was addressed to; default reply sender.
    mailbox_address = Column(String(320), nullable=True)

    # Reporter: a Computor user, or an external address (mail).
    reporter_user_id = Column(ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    reporter_email = Column(String(320), nullable=True)
    reporter_name = Column(String(255), nullable=True)

    assignee_id = Column(ForeignKey("user.id", ondelete="SET NULL"), nullable=True)

    # Optional context links (problem reports, later steps of issues#520).
    course_id = Column(ForeignKey("course.id", ondelete="SET NULL"), nullable=True)
    course_content_id = Column(ForeignKey("course_content.id", ondelete="SET NULL"), nullable=True)

    last_message_at = Column(DateTime(timezone=True), nullable=True)
    properties = Column(JSONB, nullable=True)

    reporter_user = relationship("User", foreign_keys=[reporter_user_id])
    assignee = relationship("User", foreign_keys=[assignee_id])
    messages = relationship("Message", back_populates="ticket", passive_deletes=True)
    events = relationship(
        "TicketEvent", back_populates="ticket", cascade="all, delete-orphan", passive_deletes=True
    )


class TicketEvent(Base):
    """Audit trail of ticket actions (claim, assign, status, reply, note)."""

    __tablename__ = "ticket_event"
    __table_args__ = (Index("ticket_event_ticket_idx", "ticket_id", "created_at"),)

    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    ticket_id = Column(ForeignKey("ticket.id", ondelete="CASCADE"), nullable=False)
    actor_id = Column(ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    kind = Column(String(32), nullable=False)
    data = Column(JSONB, nullable=True)

    ticket = relationship("Ticket", back_populates="events")
    actor = relationship("User", foreign_keys=[actor_id])


class TicketMailMessage(Base):
    """One RFC 5322 Message-ID known to the support system (in or out)."""

    __tablename__ = "ticket_mail_message"
    __table_args__ = (Index("ticket_mail_message_ticket_idx", "ticket_id"),)

    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    # Normalised (no angle brackets, lower-case domain part is NOT applied:
    # Message-IDs compare case-sensitively in practice).
    mail_message_id = Column(String(998), nullable=False, unique=True)
    ticket_id = Column(ForeignKey("ticket.id", ondelete="CASCADE"), nullable=False)
    message_id = Column(ForeignKey("message.id", ondelete="SET NULL"), nullable=True)


class TicketAttachment(Base):
    """Attachment of a ticket message. Download-only, never rendered inline."""

    __tablename__ = "ticket_attachment"
    __table_args__ = (Index("ticket_attachment_message_idx", "message_id"),)

    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    message_id = Column(ForeignKey("message.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(255), nullable=False)
    size = Column(Integer, nullable=False)
    # NULL when the attachment exceeded the cap; Dovecot keeps the original.
    data = Column(LargeBinary, nullable=True)


class SupportMailState(Base):
    """IMAP import cursor per folder (UIDVALIDITY + highest imported UID)."""

    __tablename__ = "support_mail_state"

    folder = Column(Text, primary_key=True)
    uidvalidity = Column(BigInteger, nullable=False)
    last_uid = Column(BigInteger, nullable=False, server_default=text("0"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
