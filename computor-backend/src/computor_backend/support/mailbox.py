"""IMAP import and SMTP replies for the team mailbox (support worker only).

Uses only the standard library (imaplib, smtplib, ssl, email). The service
credential is scoped on the mail host (computor-infra prod/TEAMMAIL.md):
IMAP rights list/read/write-flags/seen everywhere plus insert into ``Sent``,
reachable only from the support worker's network; SMTP sender restricted to
the five team addresses.

The import never changes flags (folders are SELECTed read-only and fetched
with BODY.PEEK); Dovecot stays the archive. After a reply is sent, its copy
is appended to ``Sent`` and the answered mail gets ``\\Answered``.
"""
import imaplib
import logging
import re
import smtplib
import ssl
import time
from datetime import datetime, timezone
from email.message import EmailMessage
from email.policy import SMTP as SMTP_POLICY
from email.utils import format_datetime, formataddr, make_msgid
from typing import Iterator, List, Optional, Tuple

from sqlalchemy import text as sql_text

from .config import SupportSettings

logger = logging.getLogger(__name__)

IMPORT_LOCK_KEY = 520_001  # pg advisory lock: one import at a time
_FETCH_BATCH = 25
_UIDVALIDITY = re.compile(rb"UIDVALIDITY (\d+)")
_SIZE = re.compile(rb"RFC822\.SIZE (\d+)")
_FLAGS = re.compile(rb"FLAGS \(([^)]*)\)")
_UID = re.compile(rb"UID (\d+)")


def _tls_context(settings: SupportSettings) -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if not settings.mail_tls_verify:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _quote_mailbox(name: str) -> str:
    return '"' + name.replace("\\", "\\\\").replace('"', '\\"') + '"'


class ImapError(RuntimeError):
    pass


def _ok(result, what: str):
    typ, data = result
    if typ != "OK":
        raise ImapError(f"IMAP {what} failed: {typ} {data!r}"[:500])
    return data


def imap_connect(settings: SupportSettings) -> imaplib.IMAP4_SSL:
    conn = imaplib.IMAP4_SSL(
        settings.imap_host, settings.imap_port, ssl_context=_tls_context(settings), timeout=60
    )
    _ok(conn.login(settings.imap_user, settings.imap_password), "LOGIN")
    return conn


def select_readonly(conn: imaplib.IMAP4, folder: str) -> int:
    """SELECT read-only (EXAMINE); return UIDVALIDITY."""
    _ok(conn.select(_quote_mailbox(folder), readonly=True), f"EXAMINE {folder}")
    for item in conn.untagged_responses.get("UIDVALIDITY", []) or []:
        return int(item)
    typ, data = conn.status(_quote_mailbox(folder), "(UIDVALIDITY)")
    match = _UIDVALIDITY.search(data[0] if data and data[0] else b"")
    if not match:
        raise ImapError(f"no UIDVALIDITY for {folder}")
    return int(match.group(1))


def new_uids(conn: imaplib.IMAP4, last_uid: int) -> List[int]:
    data = _ok(conn.uid("SEARCH", None, f"UID {last_uid + 1}:*"), "UID SEARCH")
    uids = [int(x) for x in (data[0] or b"").split()] if data else []
    # "n:*" always matches the highest UID, even when it is below n.
    return sorted(u for u in uids if u > last_uid)


def fetch_messages(
    conn: imaplib.IMAP4, uids: List[int], max_bytes: int
) -> Iterator[Tuple[int, bytes, List[str], int]]:
    """Yield (uid, raw, flags, oversize) without setting \\Seen.

    ``oversize`` is the size in bytes when only the header was fetched
    (message larger than ``max_bytes``), else 0."""
    for i in range(0, len(uids), _FETCH_BATCH):
        batch = uids[i:i + _FETCH_BATCH]
        sizes = {}
        data = _ok(conn.uid("FETCH", ",".join(map(str, batch)), "(UID RFC822.SIZE FLAGS)"), "FETCH size")
        for item in data:
            line = item if isinstance(item, bytes) else (item[0] if item else b"")
            u, s, f = _UID.search(line or b""), _SIZE.search(line or b""), _FLAGS.search(line or b"")
            if u:
                flags = f.group(1).decode(errors="replace").split() if f else []
                sizes[int(u.group(1))] = (int(s.group(1)) if s else 0, flags)
        for uid in batch:
            if uid not in sizes:
                continue
            size, flags = sizes[uid]
            truncated = size > max_bytes
            part = "BODY.PEEK[HEADER]" if truncated else "BODY.PEEK[]"
            data = _ok(conn.uid("FETCH", str(uid), f"({part})"), "FETCH body")
            raw = b""
            for item in data:
                if isinstance(item, tuple) and len(item) >= 2:
                    raw = item[1]
                    break
            yield uid, raw, flags, (size if truncated else 0)


def append_sent(settings: SupportSettings, raw: bytes) -> None:
    conn = imap_connect(settings)
    try:
        _ok(conn.append(_quote_mailbox(settings.sent_folder), "(\\Seen)",
                        imaplib.Time2Internaldate(time.time()), raw), "APPEND Sent")
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def mark_answered(settings: SupportSettings, folder: str, uid: int, uidvalidity: int) -> bool:
    conn = imap_connect(settings)
    try:
        _ok(conn.select(_quote_mailbox(folder)), f"SELECT {folder}")
        current = None
        for item in conn.untagged_responses.get("UIDVALIDITY", []) or []:
            current = int(item)
        if current is not None and current != uidvalidity:
            return False
        _ok(conn.uid("STORE", str(uid), "+FLAGS.SILENT", "(\\Answered)"), "STORE")
        return True
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def _display_name(name: str, suffix: str) -> str:
    name = re.sub(r"[\r\n\t\"<>]", " ", name or "").strip()
    name = re.sub(r"\s+", " ", name)[:100]
    return f"{name} {suffix}".strip() if name else suffix


def build_reply(
    settings: SupportSettings,
    *,
    sender_name: str,
    from_address: str,
    to: List[str],
    subject: str,
    body: str,
    in_reply_to: Optional[str],
    references: List[str],
    ticket_number: int,
) -> EmailMessage:
    if from_address not in settings.team_address_list:
        raise ValueError(f"sender {from_address!r} is not a team address")
    msg = EmailMessage(policy=SMTP_POLICY)
    msg["From"] = formataddr((_display_name(sender_name, settings.sender_suffix), from_address))
    msg["To"] = ", ".join(to)
    clean_subject = re.sub(r"[\r\n]+", " ", subject or "").strip() or "(no subject)"
    if not re.match(r"(?i)^re:", clean_subject):
        clean_subject = f"Re: {clean_subject}"
    msg["Subject"] = clean_subject[:900]
    msg["Date"] = format_datetime(datetime.now(timezone.utc))
    msg["Message-ID"] = make_msgid(idstring=f"ticket{ticket_number}", domain=settings.mail_domain)
    if in_reply_to:
        msg["In-Reply-To"] = f"<{in_reply_to}>"
    refs = list(dict.fromkeys([r for r in references if r] + ([in_reply_to] if in_reply_to else [])))
    if refs:
        msg["References"] = " ".join(f"<{r}>" for r in refs[-20:])
    msg["X-Computor-Ticket"] = str(ticket_number)
    msg.set_content(body)
    return msg


def smtp_send(settings: SupportSettings, msg: EmailMessage, envelope_from: str, rcpts: List[str]) -> None:
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=60) as smtp:
        smtp.ehlo()
        if settings.smtp_starttls:
            smtp.starttls(context=_tls_context(settings))
            smtp.ehlo()
        if settings.smtp_user:  # the faepmail relay accepts team mail without authentication
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg, from_addr=envelope_from, to_addrs=rcpts)


def try_import_lock(db) -> bool:
    return bool(db.execute(sql_text("SELECT pg_try_advisory_xact_lock(:k)"), {"k": IMPORT_LOCK_KEY}).scalar())
