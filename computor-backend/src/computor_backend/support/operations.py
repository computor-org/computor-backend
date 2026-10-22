"""Mail import and reply delivery, as run by the support Temporal worker.

Both are synchronous (stdlib imaplib/smtplib) and run in the worker's
activity thread pool.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, List

from sqlalchemy.orm.attributes import flag_modified

from computor_backend.database import get_db_session
from computor_backend.model.auth import User
from computor_backend.model.message import Message
from computor_backend.model.support import (
    SupportMailState,
    Ticket,
    TicketEvent,
    TicketMailMessage,
)

from . import mailbox
from .config import SupportSettings, get_support_settings
from .ingest import ingest_mail, record_unparseable
from .mailparse import parse_mail

logger = logging.getLogger(__name__)

MAX_PER_FOLDER_RUN = 300


def run_mail_import(settings: SupportSettings | None = None) -> Dict[str, int]:
    """Import new mail from every configured folder, oldest first."""
    settings = settings or get_support_settings()
    counts = {"created": 0, "threaded": 0, "duplicate": 0, "failed": 0, "skipped_locked": 0}
    if not settings.mail_enabled:
        logger.info("support mail import: disabled")
        return counts

    with get_db_session() as db:
        if not mailbox.try_import_lock(db):
            counts["skipped_locked"] = 1
            return counts

        conn = mailbox.imap_connect(settings)
        try:
            pending = []  # (date, folder, uid, uidvalidity, raw, flags, oversize)
            cursors = {}
            for folder in settings.folder_list:
                uidvalidity = mailbox.select_readonly(conn, folder)
                state = db.query(SupportMailState).filter(SupportMailState.folder == folder).first()
                if state is None:
                    state = SupportMailState(folder=folder, uidvalidity=uidvalidity, last_uid=0)
                    db.add(state)
                elif state.uidvalidity != uidvalidity:
                    # Folder recreated: re-scan; Message-ID dedup keeps it idempotent.
                    logger.warning("support mail import: UIDVALIDITY of %s changed", folder)
                    state.uidvalidity, state.last_uid = uidvalidity, 0
                cursors[folder] = state
                # Bounded per run; the next scheduled run continues.
                uids = mailbox.new_uids(conn, int(state.last_uid))[:MAX_PER_FOLDER_RUN]
                for uid, raw, flags, oversize in mailbox.fetch_messages(
                    conn, uids, settings.max_message_bytes
                ):
                    pending.append((folder, uid, uidvalidity, raw, flags, oversize))
        finally:
            try:
                conn.logout()
            except Exception:
                pass

        parsed = []
        for folder, uid, uidvalidity, raw, flags, oversize in pending:
            try:
                mail = parse_mail(raw)
                if oversize:
                    mail.text = (f"[Message of {oversize} bytes exceeds the import limit; "
                                 "read it in the team mailbox archive.]")
                    mail.html, mail.attachments = None, []
                parsed.append((mail.date, folder, uid, uidvalidity, flags, mail, None))
            except Exception as exc:  # never lose a mail silently
                logger.exception("support mail import: cannot parse %s UID %s", folder, uid)
                parsed.append((datetime.now(timezone.utc), folder, uid, uidvalidity, flags, None, str(exc)))

        # Oldest first across folders, so status follows the conversation.
        parsed.sort(key=lambda p: (p[0], p[1], p[2]))
        for _, folder, uid, uidvalidity, flags, mail, error in parsed:
            try:
                if mail is None:
                    record_unparseable(db, folder=folder, uid=uid, uidvalidity=uidvalidity, error=error)
                    counts["failed"] += 1
                else:
                    result = ingest_mail(db, mail, settings, folder=folder, uid=uid,
                                         uidvalidity=uidvalidity, flags=flags)
                    counts[result.status] += 1
            except Exception:
                logger.exception("support mail import: cannot store %s UID %s", folder, uid)
                db.rollback()
                raise
            state = cursors[folder]
            if uid > int(state.last_uid):
                state.last_uid = uid
                state.updated_at = datetime.now(timezone.utc)
        db.commit()
    logger.info("support mail import: %s", counts)
    return counts


def _sender_name(user: User | None) -> str:
    if user is None:
        return ""
    name = " ".join(p for p in (user.given_name, user.family_name) if p)
    return name


def deliver_reply(message_id: str, settings: SupportSettings | None = None) -> Dict[str, str]:
    """Send one queued reply by mail; store the copy in Sent; mark answered.

    Never retried automatically: once SMTP may have accepted the mail, a retry
    could send it twice. A failure is recorded on the message instead.
    """
    settings = settings or get_support_settings()
    with get_db_session() as db:
        message = db.query(Message).filter(Message.id == message_id).first()
        if message is None or message.ticket_id is None:
            return {"state": "missing"}
        props = dict(message.properties or {})
        mail = dict(props.get("mail") or {})
        if mail.get("state") != "queued":
            return {"state": mail.get("state") or "unknown"}
        ticket = db.query(Ticket).filter(Ticket.id == message.ticket_id).first()
        author = db.query(User).filter(User.id == message.author_id).first()

        mail["state"] = "sending"
        props["mail"] = mail
        message.properties = props
        flag_modified(message, "properties")
        db.commit()

        def fail(error: str) -> Dict[str, str]:
            mail["state"], mail["error"] = "failed", error[:500]
            props["mail"] = mail
            message.properties = dict(props)
            flag_modified(message, "properties")
            db.add(TicketEvent(ticket_id=ticket.id, actor_id=message.author_id, kind="reply_failed",
                               data={"message_id": str(message.id), "error": error[:500]}))
            db.commit()
            return {"state": "failed", "error": error[:500]}

        if not settings.mail_enabled:
            return fail("mail sending is not enabled on this deployment")
        try:
            msg = mailbox.build_reply(
                settings,
                sender_name=_sender_name(author),
                from_address=mail["from"],
                to=mail["to"],
                subject=mail.get("subject") or ticket.subject,
                body=message.content,
                in_reply_to=mail.get("in_reply_to_id"),
                references=mail.get("references") or [],
                ticket_number=int(ticket.number),
            )
            mailbox.smtp_send(settings, msg, mail["from"], mail["to"])
        except Exception as exc:
            logger.exception("support reply %s: send failed", message_id)
            return fail(f"{type(exc).__name__}: {exc}")

        mid = str(msg["Message-ID"]).strip().strip("<>")
        mail.update({
            "state": "sent",
            "message_id": mid,
            "from_header": str(msg["From"]),
            "sent_at": datetime.now(timezone.utc).isoformat(),
        })
        props["mail"] = mail
        message.properties = dict(props)
        flag_modified(message, "properties")
        db.add(TicketMailMessage(mail_message_id=mid, ticket_id=ticket.id, message_id=message.id))
        db.add(TicketEvent(ticket_id=ticket.id, actor_id=message.author_id, kind="reply_sent",
                           data={"message_id": str(message.id), "from": mail["from"], "to": mail["to"]}))
        db.commit()

        notes: List[str] = []
        try:
            mailbox.append_sent(settings, msg.as_bytes())
        except Exception as exc:
            logger.exception("support reply %s: Sent copy failed", message_id)
            notes.append(f"Sent copy failed: {type(exc).__name__}: {exc}"[:300])
        target = mail.get("answers") or {}
        if target.get("folder") and target.get("uid") and target.get("uidvalidity"):
            try:
                mailbox.mark_answered(settings, target["folder"], int(target["uid"]),
                                      int(target["uidvalidity"]))
            except Exception as exc:
                logger.warning("support reply %s: \\Answered flag failed: %s", message_id, exc)
        if notes:
            mail["notes"] = notes
            props["mail"] = mail
            message.properties = dict(props)
            flag_modified(message, "properties")
            db.commit()
        return {"state": "sent", "message_id": mid}
