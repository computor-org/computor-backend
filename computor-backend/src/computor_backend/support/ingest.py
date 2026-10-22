"""Store parsed mail as ticket messages (threading, idempotency, restriction).

Threading: a mail joins the ticket of the first of its In-Reply-To /
References Message-IDs that the system already knows (``ticket_mail_message``,
which holds every imported *and* every sent Message-ID). Otherwise it opens a
new ticket. Idempotency: a Message-ID that is already known is skipped, so
re-running the import (or importing our own sent copy from ``Sent``) never
duplicates anything; the unique index enforces it under concurrency too.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from computor_backend.model.message import Message
from computor_backend.model.support import (
    Ticket,
    TicketAttachment,
    TicketEvent,
    TicketMailMessage,
)

from .config import SupportSettings
from .mailparse import ParsedMail

logger = logging.getLogger(__name__)


@dataclass
class IngestResult:
    status: str  # "created", "threaded", "duplicate"
    ticket_id: Optional[str] = None
    message_id: Optional[str] = None


def _first_team_address(addresses: Iterable[str], team: List[str]) -> Optional[str]:
    for addr in addresses:
        if addr in team:
            return addr
    return None


def ingest_mail(
    db: Session,
    mail: ParsedMail,
    settings: SupportSettings,
    *,
    folder: str,
    uid: Optional[int] = None,
    uidvalidity: Optional[int] = None,
    flags: Iterable[str] = (),
) -> IngestResult:
    """Insert one mail. Caller commits; runs in a savepoint so a duplicate
    raced in by a concurrent import is skipped cleanly."""
    known = (
        db.query(TicketMailMessage)
        .filter(TicketMailMessage.mail_message_id == mail.message_id)
        .first()
    )
    if known is not None:
        return IngestResult("duplicate", str(known.ticket_id), str(known.message_id or ""))

    team = settings.team_address_list
    outbound = (mail.from_address in team) or folder == settings.sent_folder
    restricted_hit = any(a in settings.restricted_address_list for a in mail.all_recipients)

    ticket = None
    if mail.thread_ids:
        link = (
            db.query(TicketMailMessage)
            .filter(TicketMailMessage.mail_message_id.in_(mail.thread_ids))
            .all()
        )
        by_mid = {row.mail_message_id: row for row in link}
        for mid in mail.thread_ids:
            if mid in by_mid:
                ticket = db.query(Ticket).filter(Ticket.id == by_mid[mid].ticket_id).first()
                break

    savepoint = db.begin_nested()
    try:
        created = ticket is None
        if created:
            if outbound:
                reporter = next((a for a in mail.to + mail.cc if a not in team), None)
                reporter_name = None
                mailbox = mail.from_address if mail.from_address in team else None
            else:
                reporter = mail.from_address
                reporter_name = mail.from_name
                mailbox = _first_team_address(mail.all_recipients, team)
            ticket = Ticket(
                subject=mail.subject,
                channel="mail",
                status="waiting" if outbound else "open",
                priority="normal",
                restricted=restricted_hit,
                mailbox_address=mailbox,
                reporter_email=reporter,
                reporter_name=reporter_name,
                last_message_at=mail.date,
            )
            db.add(ticket)
            db.flush()
        else:
            if restricted_hit and not ticket.restricted:
                ticket.restricted = True
            if outbound:
                if ticket.status in ("open", "in_progress"):
                    ticket.status = "waiting"
            elif ticket.status in ("waiting", "done"):
                ticket.status = "open"
            if ticket.last_message_at is None or mail.date > ticket.last_message_at:
                ticket.last_message_at = mail.date

        mail_props = {
            "direction": "out" if outbound else "in",
            "message_id": mail.message_id,
            "in_reply_to": mail.in_reply_to,
            "references": mail.references[-50:],
            "from": mail.from_address,
            "from_name": mail.from_name,
            "to": mail.to,
            "cc": mail.cc,
            "subject": mail.subject,
            "date": mail.date.isoformat(),
            "folder": folder,
            "uid": uid,
            "uidvalidity": uidvalidity,
            "flags": sorted(set(flags)),
            "auto_submitted": mail.auto_submitted,
            "html": mail.html,
            "imported_at": datetime.now(timezone.utc).isoformat(),
        }
        message = Message(
            ticket_id=ticket.id,
            author_id=None,
            visibility="public",
            level=0,
            title=mail.subject[:255],
            content=mail.text or "",
            properties={"mail": mail_props},
            created_at=mail.date,
        )
        db.add(message)
        db.flush()

        cap = settings.max_attachment_bytes
        for att in mail.attachments:
            db.add(TicketAttachment(
                message_id=message.id,
                filename=att.filename,
                content_type=att.content_type,
                size=len(att.data),
                data=att.data if len(att.data) <= cap else None,
            ))

        db.add(TicketMailMessage(
            mail_message_id=mail.message_id, ticket_id=ticket.id, message_id=message.id
        ))
        db.add(TicketEvent(
            ticket_id=ticket.id,
            kind="mail_out" if outbound else "mail_in",
            data={"message_id": str(message.id), "folder": folder, "created": created},
        ))
        db.flush()
        savepoint.commit()
    except IntegrityError:
        savepoint.rollback()
        known = (
            db.query(TicketMailMessage)
            .filter(TicketMailMessage.mail_message_id == mail.message_id)
            .first()
        )
        if known is None:
            raise
        return IngestResult("duplicate", str(known.ticket_id), str(known.message_id or ""))

    return IngestResult("created" if created else "threaded", str(ticket.id), str(message.id))


def record_unparseable(
    db: Session, *, folder: str, uid: int, uidvalidity: int, error: str
) -> None:
    """Make a mail that could not be parsed visible instead of dropping it."""
    marker = f"unparseable-{uidvalidity}-{uid}-{folder}@computor.invalid"
    if db.query(TicketMailMessage).filter(TicketMailMessage.mail_message_id == marker).first():
        return
    ticket = Ticket(subject=f"(unreadable mail in {folder}, UID {uid})", channel="mail",
                    status="open", priority="normal", restricted=True,
                    last_message_at=datetime.now(timezone.utc))
    db.add(ticket)
    db.flush()
    message = Message(
        ticket_id=ticket.id, author_id=None, visibility="internal", level=0,
        title=ticket.subject,
        content=(f"The mail import could not parse this message ({error[:500]}). "
                 f"It is unchanged in the team mailbox, folder {folder}, UID {uid}."),
        properties={"mail": {"direction": "in", "folder": folder, "uid": uid,
                             "uidvalidity": uidvalidity}},
    )
    db.add(message)
    db.flush()
    db.add(TicketMailMessage(mail_message_id=marker, ticket_id=ticket.id, message_id=message.id))
