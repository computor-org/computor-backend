"""Support tickets against a real schema (synthetic rows only, issues#520).

Covers what must hold for the team mailbox to move into Computor:

* mail threading by In-Reply-To / References and idempotency per Message-ID;
* tickets involving security@ are restricted to _admin;
* internal notes never reach reporters, and no ticket row reaches the course
  messaging read paths (MessagePermissionHandler), not even for admins;
* role checks: _support manages, _support_agent only reads and writes notes,
  everyone else has no access; only admins grant the support roles.

Rows live in a transaction that is rolled back after each test. Skips when
Postgres is unreachable.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import sessionmaker

from computor_backend.exceptions import BadRequestException, ForbiddenException, NotFoundException
from computor_backend.model.auth import User
from computor_backend.model.message import Message
from computor_backend.model.role import Role, UserRole
from computor_backend.model.support import Ticket, TicketMailMessage
from computor_backend.permissions.core import check_permissions
from computor_backend.permissions.handlers_misc import UserRolePermissionHandler
from computor_backend.permissions.principal import Principal, build_claims
from computor_backend.support import service
from computor_backend.support.config import SupportSettings
from computor_backend.support.ingest import ingest_mail
from computor_backend.support.mailparse import parse_mail
from computor_types.support import TicketMessageCreate, TicketQuery, TicketStatus, TicketUpdate

T0 = datetime(2026, 10, 21, 8, 0, tzinfo=timezone.utc)
SETTINGS = SupportSettings(_env_file=None)


def _url() -> str:
    return (
        f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}:"
        f"{os.getenv('POSTGRES_PASSWORD', 'postgres_secret')}@"
        f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
        f"{os.getenv('POSTGRES_PORT', '5432')}/"
        f"{os.getenv('POSTGRES_DB', 'computor')}"
    )


@pytest.fixture
def db():
    try:
        engine = create_engine(_url())
        conn = engine.connect()
    except OperationalError as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"Postgres unavailable: {exc}")
    trans = conn.begin()
    session = sessionmaker(bind=conn)()
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        conn.close()
        engine.dispose()


@pytest.fixture
def people(db):
    suffix = uuid.uuid4().hex[:8]
    for rid in ("_admin", "_support", "_support_agent", "_user_manager"):
        if db.get(Role, rid) is None:
            db.add(Role(id=rid, title=rid, builtin=True))
    users = {}
    for name in ("admin", "steffi", "jakob", "agent", "student", "reporter", "manager"):
        users[name] = User(given_name=name.title(), family_name="Synthetic",
                           email=f"{name}.{suffix}@test.local")
    db.add_all(users.values())
    db.flush()
    roles = {"admin": ["_admin"], "steffi": ["_support"], "jakob": ["_support"],
             "agent": ["_support_agent"], "manager": ["_user_manager"]}
    for name, rids in roles.items():
        for rid in rids:
            db.add(UserRole(user_id=users[name].id, role_id=rid))
    db.flush()
    principals = {
        name: Principal(user_id=str(user.id), roles=roles.get(name, []))
        for name, user in users.items()
    }
    return users, principals


def _raw(mid, subject="Help", frm="ada@example.org", to="contact@computor.at", cc=None,
         in_reply_to=None, refs=None, minutes=0, body="Please help"):
    date = (T0 + timedelta(minutes=minutes)).strftime("%a, %d %b %Y %H:%M:%S +0000")
    lines = [f"From: Ada <{frm}>", f"To: {to}", f"Subject: {subject}", f"Message-ID: <{mid}>",
             f"Date: {date}"]
    if cc:
        lines.append(f"Cc: {cc}")
    if in_reply_to:
        lines.append(f"In-Reply-To: <{in_reply_to}>")
    if refs:
        lines.append("References: " + " ".join(f"<{r}>" for r in refs))
    return ("\r\n".join(lines) + "\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n" + body).encode()


def _ingest(db, raw, folder="INBOX"):
    return ingest_mail(db, parse_mail(raw), SETTINGS, folder=folder, uid=1, uidvalidity=1)


def _mid(tag):
    return f"{tag}.{uuid.uuid4().hex}@example.org"


# ------------------------------------------------------------------ threading


def test_threading_by_in_reply_to_and_references(db, people):
    root, reply1, reply2 = _mid("root"), _mid("r1"), _mid("r2")
    first = _ingest(db, _raw(root))
    assert first.status == "created"
    ticket = db.get(Ticket, first.ticket_id)
    assert ticket.status == "open" and ticket.mailbox_address == "contact@computor.at"
    assert ticket.reporter_email == "ada@example.org" and ticket.restricted is False

    # In-Reply-To only.
    assert _ingest(db, _raw(reply1, "Re: Help", in_reply_to=root, minutes=1)).ticket_id == first.ticket_id
    # References only (client that drops In-Reply-To), unknown ids ignored.
    second = _ingest(db, _raw(reply2, "Re: Help", refs=[_mid("unknown"), root], minutes=2))
    assert second.status == "threaded" and second.ticket_id == first.ticket_id

    # Same subject but no reference: a new ticket, never merged by subject.
    other = _ingest(db, _raw(_mid("other"), "Help", minutes=3))
    assert other.status == "created" and other.ticket_id != first.ticket_id


def test_import_is_idempotent_per_message_id(db, people):
    mid = _mid("dup")
    first = _ingest(db, _raw(mid))
    again = _ingest(db, _raw(mid, body="changed body, same Message-ID"))
    assert again.status == "duplicate" and again.ticket_id == first.ticket_id
    assert db.query(Message).filter(Message.ticket_id == first.ticket_id).count() == 1
    # The unique index holds even if a concurrent import raced past the check.
    savepoint = db.begin_nested()
    db.add(TicketMailMessage(mail_message_id=mid, ticket_id=first.ticket_id))
    with pytest.raises(IntegrityError):
        db.flush()
    savepoint.rollback()


def test_status_follows_conversation(db, people):
    root = _mid("root")
    t = _ingest(db, _raw(root)).ticket_id
    ours = _mid("ours")
    _ingest(db, _raw(ours, "Re: Help", frm="contact@computor.at", to="ada@example.org",
                     in_reply_to=root, minutes=1), folder="Sent")
    assert db.get(Ticket, t).status == "waiting"
    _ingest(db, _raw(_mid("back"), "Re: Help", in_reply_to=ours, minutes=2))
    assert db.get(Ticket, t).status == "open"


def test_security_address_restricts_ticket(db, people):
    users, p = people
    sec = _ingest(db, _raw(_mid("sec"), "Vuln", to="security@computor.at"))
    cc = _ingest(db, _raw(_mid("cc"), "Vuln", cc="security@computor.at"))
    plain = _ingest(db, _raw(_mid("plain"), "Hi"))
    assert db.get(Ticket, sec.ticket_id).restricted and db.get(Ticket, cc.ticket_id).restricted
    # A later mail in a thread that copies security@ restricts it (sticky).
    thread_root = _mid("thread")
    thread = _ingest(db, _raw(thread_root, "Hi again"))
    assert db.get(Ticket, thread.ticket_id).restricted is False
    _ingest(db, _raw(_mid("later"), "Re: Hi again", cc="security@computor.at",
                     in_reply_to=thread_root, minutes=5))
    _ingest(db, _raw(_mid("after"), "Re: Hi again", in_reply_to=thread_root, minutes=6))
    assert db.get(Ticket, thread.ticket_id).restricted is True

    ids_support = {t.id for t in service.list_tickets(TicketQuery(), p["steffi"], db)[0]}
    ids_admin = {t.id for t in service.list_tickets(TicketQuery(), p["admin"], db)[0]}
    assert plain.ticket_id in ids_support
    assert sec.ticket_id not in ids_support and cc.ticket_id not in ids_support
    assert thread.ticket_id not in ids_support
    assert {sec.ticket_id, cc.ticket_id, plain.ticket_id} <= ids_admin
    with pytest.raises(NotFoundException):
        service.get_ticket(sec.ticket_id, p["steffi"], db)
    with pytest.raises(NotFoundException):
        service.get_ticket(sec.ticket_id, p["agent"], db)
    assert service.get_ticket(sec.ticket_id, p["admin"], db).restricted

    # Config flag: with no restricted addresses nothing is restricted.
    open_settings = SupportSettings(_env_file=None, restricted_addresses="")
    r = ingest_mail(db, parse_mail(_raw(_mid("sec2"), to="security@computor.at")), open_settings,
                    folder="INBOX")
    assert db.get(Ticket, r.ticket_id).restricted is False


# ------------------------------------------------------------------ visibility


def test_internal_notes_and_ticket_rows_never_leak(db, people):
    users, p = people
    t = _ingest(db, _raw(_mid("leak"))).ticket_id
    service.add_message(t, TicketMessageCreate(content="internal: reporter is abusive", internal=True),
                        p["steffi"], db)
    service.add_message(t, TicketMessageCreate(content="agent draft", internal=True), p["agent"], db)
    ticket = db.get(Ticket, t)

    # A Computor user who reported the ticket sees public messages only.
    ticket.reporter_user_id = users["reporter"].id
    db.flush()
    seen = service.get_ticket(t, p["reporter"], db)
    assert [m.direction for m in seen.messages] == ["in"]
    assert all("internal" not in m.text and "draft" not in m.text for m in seen.messages)
    assert seen.events == [] and seen.message_count == 1

    # Support staff see the notes.
    staff = service.get_ticket(t, p["steffi"], db)
    assert sorted(m.direction for m in staff.messages) == ["in", "note", "note"]

    # Other users: no queue, no ticket.
    with pytest.raises(ForbiddenException):
        service.list_tickets(TicketQuery(), Principal(user_id=None, roles=[]), db)
    assert service.list_tickets(TicketQuery(), p["student"], db)[0] == []
    with pytest.raises(NotFoundException):
        service.get_ticket(t, p["student"], db)

    # Course messaging read path: no ticket row for anyone, admins included.
    for who in ("admin", "steffi", "student", "reporter"):
        visible = check_permissions(p[who], Message, "list", db)
        assert visible.filter(Message.ticket_id == t).count() == 0, who
        assert visible.filter(Message.visibility == "internal").count() == 0, who


def test_ticket_messages_cannot_carry_course_scope(db, people):
    users, _ = people
    t = _ingest(db, _raw(_mid("scope"))).ticket_id
    for bad in (dict(user_id=users["student"].id), dict(author_id=None, ticket_id=None),
                dict(visibility="internal", ticket_id=None)):
        fields = dict(ticket_id=t, author_id=users["steffi"].id, visibility="public", level=0,
                      content="x")
        fields.update(bad)
        savepoint = db.begin_nested()
        db.add(Message(**fields))
        with pytest.raises(IntegrityError):
            db.flush()
        savepoint.rollback()


def test_course_message_cannot_reply_to_ticket_message(db, people):
    from computor_backend.business_logic.messages.core import create_message_with_author
    from computor_types.messages import MessageCreate

    users, p = people
    t = _ingest(db, _raw(_mid("parent"))).ticket_id
    ticket_msg = db.query(Message).filter(Message.ticket_id == t).first()
    with pytest.raises(BadRequestException):
        create_message_with_author(MessageCreate(content="hi", parent_id=str(ticket_msg.id)),
                                   p["admin"], db)


# ------------------------------------------------------------------ roles


def test_role_checks(db, people):
    users, p = people
    t = _ingest(db, _raw(_mid("roles"))).ticket_id

    # Agent: may note, may not claim, assign, set status or reply.
    with pytest.raises(ForbiddenException):
        service.claim_ticket(t, p["agent"], db)
    with pytest.raises(ForbiddenException):
        service.update_ticket(t, TicketUpdate(status=TicketStatus.DONE), p["agent"], db)
    with pytest.raises(ForbiddenException):
        service.add_message(t, TicketMessageCreate(content="reply"), p["agent"], db)
    # Ordinary users cannot even see it; a user manager is an ordinary user here.
    for who in ("student", "manager"):
        with pytest.raises(NotFoundException):
            service.get_ticket(t, p[who], db)
        with pytest.raises(ForbiddenException):
            service.claim_ticket(t, p[who], db)

    # Support: claim, assign to a colleague, status, reply.
    claimed = service.claim_ticket(t, p["steffi"], db)
    assert claimed.assignee.id == str(users["steffi"].id) and claimed.status == "in_progress"
    moved = service.update_ticket(t, TicketUpdate(assignee_id=str(users["jakob"].id)), p["steffi"], db)
    assert moved.assignee.id == str(users["jakob"].id)
    with pytest.raises(BadRequestException):  # not a support member
        service.update_ticket(t, TicketUpdate(assignee_id=str(users["student"].id)), p["steffi"], db)
    mine = service.list_tickets(TicketQuery(scope="mine"), p["jakob"], db)[0]
    assert [x.id for x in mine] == [t]
    assert t not in {x.id for x in service.list_tickets(TicketQuery(scope="unassigned"), p["jakob"], db)[0]}

    sent, to_send = service.add_message(
        t, TicketMessageCreate(content="We fixed it", from_address="privacy@computor.at"), p["jakob"], db)
    out = [m for m in sent.messages if m.direction == "out"][0]
    assert to_send == out.id and out.delivery_state == "queued"
    assert out.author.id == str(users["jakob"].id)  # audit: the Computor user
    assert sent.status == "waiting"
    with pytest.raises(BadRequestException):  # never from a non-team address
        service.add_message(t, TicketMessageCreate(content="x", from_address="noreply@computor.at"),
                            p["jakob"], db)
    done = service.update_ticket(t, TicketUpdate(status=TicketStatus.DONE), p["steffi"], db)
    assert done.status == "done"
    kinds = [e.kind for e in done.events]
    assert {"mail_in", "claim", "update", "reply"} <= set(kinds)

    # Restricted tickets can only be assigned to admins.
    sec = _ingest(db, _raw(_mid("sec"), to="security@computor.at")).ticket_id
    with pytest.raises(BadRequestException):
        service.update_ticket(sec, TicketUpdate(assignee_id=str(users["steffi"].id)), p["admin"], db)
    ok = service.update_ticket(sec, TicketUpdate(assignee_id=str(users["admin"].id)), p["admin"], db)
    assert ok.assignee.id == str(users["admin"].id)


def test_only_admins_grant_support_roles(db, people):
    users, _ = people
    handler = UserRolePermissionHandler(UserRole)
    manager = Principal(
        user_id=str(users["manager"].id), roles=["_user_manager"],
        claims=build_claims([("permissions", "user_role:create"), ("permissions", "user_role:delete")]),
    )
    for role in ("_support", "_support_agent", "_admin"):
        with pytest.raises(ForbiddenException):
            handler.can_perform_action(manager, "create", context={"role_id": role})
    assert handler.can_perform_action(manager, "create", context={"role_id": "_workspace_user"})
    # Existing support assignments are invisible to the manager's delete query.
    deletable = handler.build_query(manager, "delete", db)
    assert deletable.filter(UserRole.role_id == "_support").count() == 0
