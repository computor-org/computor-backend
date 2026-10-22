"""Ticket operations behind the /support endpoints."""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from computor_backend.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from computor_backend.model.auth import User
from computor_backend.model.message import Message
from computor_backend.model.role import UserRole
from computor_backend.model.support import Ticket, TicketAttachment, TicketEvent
from computor_backend.permissions.principal import Principal
from computor_backend.permissions.roles import SUPPORT_ROLE
from computor_types.support import (
    SupportAgentRef,
    TicketAttachmentGet,
    TicketEventGet,
    TicketGet,
    TicketList,
    TicketMessageCreate,
    TicketMessageGet,
    TicketQuery,
    TicketUpdate,
    TicketUserRef,
)

from . import access
from .config import get_support_settings

logger = logging.getLogger(__name__)


def _user_ref(user: Optional[User]) -> Optional[TicketUserRef]:
    if user is None:
        return None
    return TicketUserRef(id=str(user.id), given_name=user.given_name,
                         family_name=user.family_name, email=user.email)


def _require_view(principal: Principal, db: Session):
    query = access.visible_tickets(principal, db)
    if query is None:
        raise ForbiddenException(detail="No access to support tickets")
    return query


def get_ticket_or_404(ticket_id: str, principal: Principal, db: Session) -> Ticket:
    ticket = _require_view(principal, db).filter(Ticket.id == str(ticket_id)).first()
    if ticket is None:
        # Restricted and foreign tickets are indistinguishable from missing ones.
        raise NotFoundException(detail="Ticket not found")
    return ticket


def _counts(ticket_ids: List[str], principal: Principal, db: Session) -> Dict[str, int]:
    if not ticket_ids:
        return {}
    q = db.query(Message.ticket_id, func.count(Message.id)).filter(Message.ticket_id.in_(ticket_ids))
    if not access.sees_internal(principal):
        q = q.filter(Message.visibility == "public")
    return {str(tid): n for tid, n in q.group_by(Message.ticket_id).all()}


def _to_list(ticket: Ticket, count: int) -> TicketList:
    return TicketList(
        id=str(ticket.id), number=int(ticket.number), subject=ticket.subject,
        channel=ticket.channel, status=ticket.status, priority=ticket.priority,
        restricted=bool(ticket.restricted), mailbox_address=ticket.mailbox_address,
        reporter_email=ticket.reporter_email, reporter_name=ticket.reporter_name,
        reporter_user_id=str(ticket.reporter_user_id) if ticket.reporter_user_id else None,
        assignee=_user_ref(ticket.assignee), message_count=count,
        last_message_at=ticket.last_message_at, created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


def list_tickets(params: TicketQuery, principal: Principal, db: Session) -> Tuple[List[TicketList], int]:
    query = _require_view(principal, db)
    if params.scope == "unassigned":
        query = query.filter(Ticket.assignee_id.is_(None))
    elif params.scope == "mine":
        query = query.filter(Ticket.assignee_id == principal.user_id)
    if params.status is not None:
        query = query.filter(Ticket.status == params.status.value)
    if params.search:
        like = f"%{params.search.replace('%', '').replace('_', '')}%"
        query = query.filter(or_(Ticket.subject.ilike(like), Ticket.reporter_email.ilike(like),
                                 Ticket.reporter_name.ilike(like)))
    total = query.order_by(None).count()
    rows = (query.order_by(func.coalesce(Ticket.last_message_at, Ticket.created_at).desc(),
                           Ticket.number.desc())
            .offset(params.skip).limit(params.limit).all())
    counts = _counts([str(t.id) for t in rows], principal, db)
    return [_to_list(t, counts.get(str(t.id), 0)) for t in rows], total


def _message_dto(m: Message, attachments: List[TicketAttachment], authors: Dict[str, User]) -> TicketMessageGet:
    mail = (m.properties or {}).get("mail") or {}
    if m.visibility == "internal":
        direction = "note"
    elif mail.get("direction") == "in":
        direction = "in"
    else:
        direction = "out"
    return TicketMessageGet(
        id=str(m.id), visibility=m.visibility, direction=direction,
        author=_user_ref(authors.get(str(m.author_id))) if m.author_id else None,
        from_address=mail.get("from"), from_name=mail.get("from_name"),
        to=mail.get("to") or [], cc=mail.get("cc") or [], subject=mail.get("subject") or m.title,
        text=m.content or "", html=mail.get("html") if direction != "note" else None,
        attachments=[TicketAttachmentGet(id=str(a.id), filename=a.filename,
                                         content_type=a.content_type, size=a.size,
                                         stored=a.data is not None) for a in attachments],
        delivery_state=mail.get("state") if direction == "out" and m.author_id else None,
        delivery_error=mail.get("error"),
        created_at=m.created_at,
    )


def ticket_messages(ticket: Ticket, principal: Principal, db: Session) -> List[Message]:
    q = db.query(Message).filter(Message.ticket_id == ticket.id, Message.archived_at.is_(None))
    if not access.sees_internal(principal):
        q = q.filter(Message.visibility == "public")
    return q.order_by(Message.created_at.asc(), Message.id.asc()).all()


def get_ticket(ticket_id: str, principal: Principal, db: Session) -> TicketGet:
    ticket = get_ticket_or_404(ticket_id, principal, db)
    messages = ticket_messages(ticket, principal, db)
    ids = [str(m.id) for m in messages]
    atts: Dict[str, List[TicketAttachment]] = {}
    if ids:
        for a in (db.query(TicketAttachment.id, TicketAttachment.message_id, TicketAttachment.filename,
                           TicketAttachment.content_type, TicketAttachment.size,
                           (TicketAttachment.data.isnot(None)).label("stored"))
                  .filter(TicketAttachment.message_id.in_(ids)).all()):
            atts.setdefault(str(a.message_id), []).append(
                TicketAttachment(id=a.id, message_id=a.message_id, filename=a.filename,
                                 content_type=a.content_type, size=a.size,
                                 data=b"" if a.stored else None))
    author_ids = {str(m.author_id) for m in messages if m.author_id}
    authors = {str(u.id): u for u in db.query(User).filter(User.id.in_(author_ids)).all()} if author_ids else {}
    base = _to_list(ticket, len(messages))
    events: List[TicketEventGet] = []
    if access.sees_internal(principal):
        rows = (db.query(TicketEvent).filter(TicketEvent.ticket_id == ticket.id)
                .order_by(TicketEvent.created_at.asc()).all())
        events = [TicketEventGet(id=str(e.id), kind=e.kind, actor=_user_ref(e.actor),
                                 data=e.data or {}, created_at=e.created_at) for e in rows]
    return TicketGet(**base.model_dump(),
                     messages=[_message_dto(m, atts.get(str(m.id), []), authors) for m in messages],
                     events=events)


def _event(db: Session, ticket: Ticket, principal: Principal, kind: str, data: dict) -> None:
    db.add(TicketEvent(ticket_id=ticket.id, actor_id=principal.user_id, kind=kind, data=data))


def _touch(ticket: Ticket) -> None:
    ticket.updated_at = datetime.now(timezone.utc)


def claim_ticket(ticket_id: str, principal: Principal, db: Session) -> TicketGet:
    if not access.can_manage(principal):
        raise ForbiddenException(detail="Only support members can claim tickets")
    ticket = get_ticket_or_404(ticket_id, principal, db)
    previous = str(ticket.assignee_id) if ticket.assignee_id else None
    ticket.assignee_id = principal.user_id
    if ticket.status == "open":
        ticket.status = "in_progress"
    _touch(ticket)
    _event(db, ticket, principal, "claim", {"previous_assignee": previous})
    db.commit()
    return get_ticket(ticket_id, principal, db)


def _global_roles(user_id: str, db: Session) -> List[str]:
    return [r[0] for r in db.query(UserRole.role_id).filter(UserRole.user_id == user_id).all()]


def update_ticket(ticket_id: str, payload: TicketUpdate, principal: Principal, db: Session) -> TicketGet:
    if not access.can_manage(principal):
        raise ForbiddenException(detail="Only support members can change tickets")
    ticket = get_ticket_or_404(ticket_id, principal, db)
    changes = {}
    if payload.status is not None and payload.status.value != ticket.status:
        changes["status"] = [ticket.status, payload.status.value]
        ticket.status = payload.status.value
    if payload.priority is not None and payload.priority.value != ticket.priority:
        changes["priority"] = [ticket.priority, payload.priority.value]
        ticket.priority = payload.priority.value
    if payload.unassign and ticket.assignee_id is not None:
        changes["assignee"] = [str(ticket.assignee_id), None]
        ticket.assignee_id = None
    elif payload.assignee_id:
        target = db.query(User).filter(User.id == payload.assignee_id, User.archived_at.is_(None)).first()
        if target is None or not access.assignable(_global_roles(str(target.id), db), bool(ticket.restricted)):
            raise BadRequestException(detail="Assignee must be an active support member")
        if str(ticket.assignee_id or "") != str(target.id):
            changes["assignee"] = [str(ticket.assignee_id) if ticket.assignee_id else None, str(target.id)]
            ticket.assignee_id = target.id
    if changes:
        _touch(ticket)
        _event(db, ticket, principal, "update", changes)
        db.commit()
    return get_ticket(ticket_id, principal, db)


def _last_inbound(ticket: Ticket, db: Session) -> Optional[Message]:
    rows = (db.query(Message).filter(Message.ticket_id == ticket.id, Message.visibility == "public")
            .order_by(Message.created_at.desc()).limit(50).all())
    for m in rows:
        if ((m.properties or {}).get("mail") or {}).get("direction") == "in":
            return m
    return None


def add_message(ticket_id: str, payload: TicketMessageCreate, principal: Principal,
                db: Session) -> Tuple[TicketGet, Optional[str]]:
    """Add an internal note or a public mail reply. Returns (ticket, message id to send)."""
    ticket = get_ticket_or_404(ticket_id, principal, db)
    content = payload.content.strip()
    if not content:
        raise BadRequestException(detail="Content is required")

    if payload.internal:
        if not access.can_write_internal(principal):
            raise ForbiddenException(detail="Not allowed to write internal notes")
        msg = Message(ticket_id=ticket.id, author_id=principal.user_id, visibility="internal",
                      level=0, title=None, content=content, properties={"note": True})
        db.add(msg)
        db.flush()
        _event(db, ticket, principal, "note", {"message_id": str(msg.id)})
        _touch(ticket)
        db.commit()
        return get_ticket(ticket_id, principal, db), None

    if not access.can_manage(principal):
        raise ForbiddenException(detail="Only support members can reply")
    if ticket.channel != "mail":
        raise BadRequestException(detail="Only mail tickets can be answered by mail")
    settings = get_support_settings()
    team = settings.team_address_list
    sender = (payload.from_address or ticket.mailbox_address or (team[0] if team else "")).strip().lower()
    if sender not in team:
        raise BadRequestException(detail="Replies can only be sent from a team address",
                                  context={"allowed": team})
    if not ticket.reporter_email:
        raise BadRequestException(detail="The ticket has no reporter address to reply to")

    target = _last_inbound(ticket, db)
    tmail = ((target.properties or {}).get("mail") or {}) if target else {}
    mail = {
        "direction": "out",
        "state": "queued",
        "from": sender,
        "to": [ticket.reporter_email],
        "subject": tmail.get("subject") or ticket.subject,
        "in_reply_to_id": tmail.get("message_id"),
        "references": list(tmail.get("references") or []),
        "answers": ({"folder": tmail.get("folder"), "uid": tmail.get("uid"),
                     "uidvalidity": tmail.get("uidvalidity")} if tmail.get("uid") else None),
        "queued_at": datetime.now(timezone.utc).isoformat(),
    }
    msg = Message(ticket_id=ticket.id, author_id=principal.user_id, visibility="public", level=0,
                  title=mail["subject"][:255], content=content, properties={"mail": mail})
    db.add(msg)
    db.flush()
    _event(db, ticket, principal, "reply", {"message_id": str(msg.id), "from": sender,
                                            "to": mail["to"]})
    if ticket.status in ("open", "in_progress"):
        ticket.status = "waiting"
    if ticket.assignee_id is None:
        ticket.assignee_id = principal.user_id
    ticket.last_message_at = datetime.now(timezone.utc)
    _touch(ticket)
    db.commit()
    return get_ticket(ticket_id, principal, db), str(msg.id)


def mark_delivery_failed(message_id: str, error: str, db: Session) -> None:
    from sqlalchemy.orm.attributes import flag_modified
    m = db.query(Message).filter(Message.id == message_id).first()
    if m is None:
        return
    props = dict(m.properties or {})
    mail = dict(props.get("mail") or {})
    mail["state"], mail["error"] = "failed", error[:500]
    props["mail"] = mail
    m.properties = props
    flag_modified(m, "properties")
    db.commit()


def requeue_failed(ticket: Ticket, message_id: str, principal: Principal, db: Session) -> str:
    """Set a failed reply back to queued; refuses anything else."""
    from sqlalchemy.orm.attributes import flag_modified
    m = (db.query(Message).filter(Message.id == message_id, Message.ticket_id == ticket.id,
                                  Message.visibility == "public").first())
    mail = dict(((m.properties or {}).get("mail") or {})) if m else {}
    if m is None or mail.get("state") != "failed":
        raise BadRequestException(detail="Only a failed reply can be sent again")
    mail["state"] = "queued"
    mail.pop("error", None)
    m.properties = {**(m.properties or {}), "mail": mail}
    flag_modified(m, "properties")
    _event(db, ticket, principal, "reply_retry", {"message_id": str(m.id)})
    db.commit()
    return str(m.id)


def get_attachment(ticket_id: str, attachment_id: str, principal: Principal, db: Session) -> TicketAttachment:
    ticket = get_ticket_or_404(ticket_id, principal, db)
    q = (db.query(TicketAttachment).join(Message, Message.id == TicketAttachment.message_id)
         .filter(TicketAttachment.id == attachment_id, Message.ticket_id == ticket.id))
    if not access.sees_internal(principal):
        q = q.filter(Message.visibility == "public")
    att = q.first()
    if att is None or att.data is None:
        raise NotFoundException(detail="Attachment not found")
    return att


def list_agents(principal: Principal, db: Session) -> List[SupportAgentRef]:
    if not access.can_view_team_queue(principal):
        raise ForbiddenException(detail="No access to support tickets")
    rows = (db.query(User, UserRole.role_id).join(UserRole, UserRole.user_id == User.id)
            .filter(or_(UserRole.role_id == SUPPORT_ROLE, UserRole.role_id == "_admin"),
                    User.archived_at.is_(None), User.is_service.is_(False))
            .all())
    by_id: Dict[str, SupportAgentRef] = {}
    for user, role in rows:
        ref = by_id.setdefault(str(user.id), SupportAgentRef(
            id=str(user.id), given_name=user.given_name, family_name=user.family_name,
            email=user.email, roles=[]))
        ref.roles.append(role)
    return sorted(by_id.values(), key=lambda r: ((r.family_name or ""), (r.given_name or "")))
