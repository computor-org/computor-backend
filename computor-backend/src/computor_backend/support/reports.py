"""Problem reports as support tickets (computor-org/issues#520, step 2).

"Report a Problem" in computor-web and the VS Code extension files a ticket
(channel ``web`` / ``vscode``) whose reporter is the signed-in user. Nothing is
posted anywhere public: a ``_support`` member may later publish an anonymised,
hand-edited summary as a GitHub issue (``publish_ticket``), which reuses the
``issue_report`` table so the reporter link stays admin-only as before.
"""
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from computor_backend.exceptions import BadRequestException, ConflictException, ForbiddenException
from computor_backend.model.auth import User
from computor_backend.model.message import Message
from computor_backend.model.support import Ticket, TicketAttachment, TicketEvent
from computor_backend.permissions.principal import Principal
from computor_types.issue_reports import IssueReportCreate
from computor_types.support import TicketPublishDraft

from . import access

logger = logging.getLogger(__name__)

# Context is stored for the team only, so only credentials are removed here.
# Publishing applies the stricter identity redaction of the GitHub path.
_SECRET_KEY_RE = re.compile(
    r"(?:token|secret|password|authorization|cookie|credential|private[_-]?key)", re.IGNORECASE
)
_CHANNELS = ("web", "vscode")


def _strip_secrets(value: Any, depth: int = 0) -> Any:
    if depth > 5:
        return "[truncated]"
    if isinstance(value, dict):
        return {str(k): "[redacted]" if _SECRET_KEY_RE.search(str(k)) else _strip_secrets(v, depth + 1)
                for k, v in list(value.items())[:100]}
    if isinstance(value, list):
        return [_strip_secrets(v, depth + 1) for v in value[:100]]
    if isinstance(value, str) and len(value) > 2000:
        return f"{value[:2000]}… [truncated]"
    return value


def resolve_channel(requested: Optional[str], context: dict) -> str:
    """``web`` or ``vscode``: the explicit form field, else the client name."""
    if requested in _CHANNELS:
        return requested
    client = str(context.get("client") or "").lower()
    return "vscode" if "vscode" in client else "web"


def _report_text(payload: IssueReportCreate) -> str:
    parts = [payload.description.strip()]
    if payload.expected and payload.expected.strip():
        parts.append("Expected:\n" + payload.expected.strip())
    if payload.steps and payload.steps.strip():
        parts.append("Steps to reproduce:\n" + payload.steps.strip())
    return "\n\n".join(parts)


def report_subject(payload: IssueReportCreate) -> str:
    source = (payload.title or payload.description.strip().splitlines()[0]).strip()
    return " ".join(source.split())[:160] or "Problem report"


def create_report_ticket(
    payload: IssueReportCreate,
    channel: str,
    principal: Principal,
    db: Session,
    screenshot: Optional[Tuple[bytes, str, str]] = None,
    log: Optional[Tuple[bytes, str]] = None,
) -> Ticket:
    """File one problem report as an open ticket with its first message.

    ``screenshot`` is ``(bytes, content_type, filename)``, ``log`` is
    ``(bytes, filename)``; both are what the user chose to attach and are
    stored download-only like mail attachments.
    """
    user_id = principal.get_user_id_or_throw()
    user = db.query(User).filter(User.id == user_id).first()
    name = " ".join(p for p in ((user.given_name if user else None),
                                (user.family_name if user else None)) if p) or None
    context = _strip_secrets(payload.context or {})
    now = datetime.now(timezone.utc)
    ticket = Ticket(
        subject=report_subject(payload), channel=channel, status="open", priority="normal",
        restricted=False, reporter_user_id=user_id,
        reporter_email=(user.email if user else None), reporter_name=name,
        last_message_at=now,
        properties={"report": {
            "context": context,
            "app": context.get("client"),
            "version": context.get("client_version"),
            "page": context.get("page"),
            "command": context.get("command"),
        }},
    )
    db.add(ticket)
    db.flush()
    msg = Message(ticket_id=ticket.id, author_id=user_id, visibility="public", level=0,
                  title=ticket.subject[:255], content=_report_text(payload),
                  properties={"direction": "in", "report": True})
    db.add(msg)
    db.flush()
    if screenshot is not None:
        data, content_type, filename = screenshot
        db.add(TicketAttachment(message_id=msg.id, filename=filename, content_type=content_type,
                                size=len(data), data=data))
    if log is not None:
        data, filename = log
        db.add(TicketAttachment(message_id=msg.id, filename=filename, content_type="text/plain",
                                size=len(data), data=data))
    db.add(TicketEvent(ticket_id=ticket.id, actor_id=user_id, kind="report",
                       data={"channel": channel}))
    db.commit()
    db.refresh(ticket)
    return ticket


# ------------------------------------------------------------------ publish


def _first_report_message(ticket: Ticket, db: Session) -> Optional[Message]:
    return (db.query(Message)
            .filter(Message.ticket_id == ticket.id, Message.visibility == "public")
            .order_by(Message.created_at.asc(), Message.id.asc()).first())


def publish_draft(ticket: Ticket, principal: Principal, db: Session) -> TicketPublishDraft:
    """A starting point for the anonymised issue; the support member edits it."""
    if not access.can_manage(principal):
        raise ForbiddenException(detail="Only support members can publish tickets")
    from computor_backend.issue_reports.service import _redact

    first = _first_report_message(ticket, db)
    report = (ticket.properties or {}).get("report") or {}
    context_json = json.dumps(_redact(report.get("context") or {}), indent=2, sort_keys=True,
                              default=str)[:16_000]
    body = "\n".join([
        "## Description",
        (first.content if first else "").strip() or "Not provided.",
        "",
        "## Client context",
        "```json",
        context_json,
        "```",
    ])
    return TicketPublishDraft(title=f"[User report] {ticket.subject}"[:160], body=body)


async def publish_ticket(ticket: Ticket, title: str, body: str, principal: Principal,
                         db: Session) -> None:
    """Create the GitHub issue and record it on the ticket (once)."""
    if not access.can_manage(principal):
        raise ForbiddenException(detail="Only support members can publish tickets")
    if ticket.restricted:
        raise ForbiddenException(detail="Restricted tickets are never published")
    props = dict(ticket.properties or {})
    if props.get("github"):
        raise ConflictException(detail="This ticket has already been published")
    title, body = title.strip(), body.strip()
    if not title or not body:
        raise BadRequestException(detail="Title and text are required")
    from computor_backend.issue_reports.service import publish_issue

    record = await publish_issue(title, body,
                                 str(ticket.reporter_user_id) if ticket.reporter_user_id else None, db)
    props["github"] = {
        "report_id": str(record.id),
        "repository": record.repository,
        "issue_number": record.issue_number,
        "issue_url": record.issue_url,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "published_by": principal.user_id,
    }
    ticket.properties = props
    flag_modified(ticket, "properties")
    ticket.updated_at = datetime.now(timezone.utc)
    db.add(TicketEvent(ticket_id=ticket.id, actor_id=principal.user_id, kind="publish",
                       data={"issue_number": record.issue_number, "issue_url": record.issue_url}))
    db.commit()
