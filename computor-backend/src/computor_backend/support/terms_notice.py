"""One-time notice of a Terms of Use change to existing accounts (terms 1.6).

Clause 11 of the earlier terms (1.0 to 1.3) requires notice by email at least
30 days before new terms take effect. This job sends that email once to every
account holder with a verified address and records the delivery in
``User.properties["legal"]["terms_notice"][VERSION]``, so a rerun sends nothing
twice and only retries failed or new recipients.

Run it where SMTP is configured, i.e. in the support worker container::

    python -m computor_backend.support.terms_notice --effective-from 2026-12-07
    python -m computor_backend.support.terms_notice --effective-from 2026-12-07 --apply

Without ``--apply`` it is a dry run that prints counts only. Output never
contains addresses or names. The effective date is the same value as the web
build's NEXT_PUBLIC_TERMS_EFFECTIVE_FROM (computor-web/src/config/terms.ts).

Recipients: users with an email that an SSO login verified for that address
(the rule of ``scripts/audit_unverified_sso_users.classify``), not service
accounts, not archived (deleted) and created before the run started. Banned
accounts keep their contract and are notified too.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from email.policy import SMTP as SMTP_POLICY
from email.utils import format_datetime, formataddr, make_msgid
from typing import Callable, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from . import mailbox
from .config import SupportSettings, get_support_settings

logger = logging.getLogger(__name__)

VERSION = "1.6"
SENDER = "contact@computor.at"
MIN_NOTICE_DAYS = 30
_LOCK_KEY = 0x7465726D  # "term": one notice run at a time
# Version 1.0, which most existing accounts accepted (the changes page links all).
OLD_VERSION_URL = (
    "https://github.com/computor-org/computor-backend/blob/"
    "54ea77021304f1bd77ef4bf7c5712b5edfb6843f/computor-web/content/legal/{}"
)

_DE = """Hallo {name_de},

ab {date_de} gelten für computor.at die Nutzungsbedingungen in Version 1.6. Das Wichtigste:
- Anmeldung mit E-Mail-Adresse und Passwort statt über GitHub.
- Lernhilfen einschließlich KI (Lena) als zusätzliche Leistung; in manchen Kursen werden Fragen automatisch Lena zugeordnet.
- Mehr erlaubt: Netzwerkdienste und Sicherheitsübungen, wenn dein Kurs sie vorsieht.
- Unverändert: 30 Tage Vorankündigung per E-Mail; Änderungen zu deinem Nachteil gelten nur mit deiner Zustimmung.
Was sich ändert: {url}/terms/changes · bisherige Fassung: {old_de} · Datenschutzerklärung 1.6: {url}/privacy
Du musst nichts tun. Wenn du nicht einverstanden bist, kannst du jederzeit kündigen und die Löschung deines Kontos verlangen (privacy@computor.at). Fragen? Antworte einfach auf diese Mail.
"""

_EN = """Hello {name_en},

from {date_en}, version 1.6 of the computor.at Terms of Use applies. The main points:
- Sign-in with email and password instead of GitHub.
- Learning aids including AI (Lena) as an additional service; in some courses questions are routed to Lena automatically.
- More allowed: network services and security exercises where your course provides them.
- Unchanged: 30 days' notice by email; changes to your disadvantage apply only with your consent.
What changes: {url}/terms/en/changes · previous version: {old_en} · Privacy notice 1.6: {url}/privacy/en
You do not need to do anything. If you disagree, you may terminate at any time and request deletion of your account (privacy@computor.at). Questions? Just reply to this email.
"""

_SIGNATURE = "\nDein computor.at-Team, TU Graz / Your computor.at team, TU Graz\n"


_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August",
           "September", "October", "November", "December")


def format_date(value: date, language: str) -> str:
    """As the web pages write it (computor-web/src/config/terms.ts)."""
    if language == "de":
        return value.strftime("%d.%m.%Y")
    return f"{value.day} {_MONTHS[value.month - 1]} {value.year}"


def build_notice(*, given_name: str, to: str, effective_from: date, site_url: str,
                 mail_domain: str = "computor.at") -> EmailMessage:
    """German first, then English: the account language is not stored reliably."""
    name = " ".join((given_name or "").split())
    url = site_url.rstrip("/")
    fields = {
        "name_de": name or "zusammen", "name_en": name or "there", "url": url,
        "old_de": OLD_VERSION_URL.format("nutzungsbedingungen_de.md"),
        "old_en": OLD_VERSION_URL.format("terms_en.md"),
        "date_de": format_date(effective_from, "de"), "date_en": format_date(effective_from, "en"),
    }
    msg = EmailMessage(policy=SMTP_POLICY)
    msg["From"] = formataddr(("computor.at", SENDER))
    msg["To"] = to
    msg["Subject"] = (f"computor.at: neue Nutzungsbedingungen ab {fields['date_de']} / "
                      f"new Terms of Use from {fields['date_en']}")
    msg["Date"] = format_datetime(datetime.now(timezone.utc))
    msg["Message-ID"] = make_msgid(idstring="terms-notice", domain=mail_domain)
    msg["Auto-Submitted"] = "auto-generated"
    msg.set_content(_DE.format(**fields) + "\n---\n\n" + _EN.format(**fields) + _SIGNATURE)
    return msg


@dataclass
class Recipient:
    user_id: str
    email: str
    given_name: str


def _notified(properties: Optional[dict]) -> bool:
    legal = (properties or {}).get("legal") or {}
    return VERSION in ((legal.get("terms_notice") or {}))


def select(db: Session, created_before: datetime) -> Dict[str, object]:
    """Eligible recipients and counts. ``pending`` are those not yet notified."""
    from computor_backend.model.auth import Account, User
    from computor_backend.scripts.audit_unverified_sso_users import classify

    users = (
        db.query(User)
        .filter(User.email.isnot(None), User.is_service.is_(False), User.archived_at.is_(None),
                User.created_at < created_before)
        .all()
    )
    accounts: Dict[str, List[dict]] = {}
    if users:
        rows = (db.query(Account.user_id, Account.properties)
                .filter(Account.builtin.is_(True), Account.user_id.in_([u.id for u in users])).all())
        for user_id, properties in rows:
            accounts.setdefault(str(user_id), []).append(properties)
    pending: List[Recipient] = []
    unverified = done = 0
    for user in users:
        if classify(user.email, accounts.get(str(user.id), [])) != "verified":
            unverified += 1
        elif _notified(user.properties):
            done += 1
        else:
            pending.append(Recipient(str(user.id), user.email, user.given_name or ""))
    return {"pending": pending, "already_notified": done, "unverified": unverified,
            "eligible": done + len(pending)}


def _record(db: Session, user_id: str, sent_at: datetime) -> None:
    from computor_backend.model.auth import User

    user = db.query(User).filter(User.id == user_id).with_for_update().one()
    properties = dict(user.properties or {})
    legal = dict(properties.get("legal") or {})
    notices = dict(legal.get("terms_notice") or {})
    notices[VERSION] = sent_at.isoformat()
    legal["terms_notice"] = notices
    properties["legal"] = legal
    user.properties = properties
    flag_modified(user, "properties")
    db.commit()


class _RunLock:
    """Session-level advisory lock on a connection of its own: the ORM session
    returns its connection to the pool on every commit."""

    def __init__(self, db: Session):
        bind = db.get_bind()
        self._own = isinstance(bind, Engine)
        self._conn = bind.connect() if self._own else bind
        if not self._conn.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": _LOCK_KEY}).scalar():
            if self._own:
                self._conn.close()
            self._conn = None
            raise SystemExit("another terms notice run holds the lock")

    def release(self) -> None:
        if self._conn is None:
            return
        self._conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": _LOCK_KEY})
        if self._own:
            self._conn.close()
        self._conn = None


def run(db: Session, *, effective_from: date, apply: bool, site_url: str,
        settings: SupportSettings, per_minute: int = 30, allow_short_notice: bool = False,
        now: Optional[datetime] = None, send: Optional[Callable[[EmailMessage, str], None]] = None,
        sleep: Callable[[float], None] = time.sleep, out=print) -> Dict[str, int]:
    """Dry run (counts) or send. Returns the counts it printed."""
    now = now or datetime.now(timezone.utc)
    if apply:
        if not settings.mail_enabled:
            raise SystemExit("SUPPORT_MAIL_ENABLED is off: no SMTP on this process")
        if SENDER not in settings.team_address_list:
            raise SystemExit(f"{SENDER} is not a team address")
        days = (effective_from - now.date()).days
        if days < MIN_NOTICE_DAYS and not allow_short_notice:
            raise SystemExit(f"effective date is {days} days away; terms 1.0 §11 needs at least "
                             f"{MIN_NOTICE_DAYS} (--allow-short-notice for late recipients)")
    lock = _RunLock(db) if apply else None
    send = send or (lambda msg, rcpt: mailbox.smtp_send(settings, msg, SENDER, [rcpt]))
    try:
        found = select(db, now)
        pending: List[Recipient] = found["pending"]  # type: ignore[assignment]
        counts = {"eligible": found["eligible"], "already_notified": found["already_notified"],
                  "skipped_unverified": found["unverified"], "sent": 0, "failed": 0}
        out(f"terms notice {VERSION}, effective {effective_from.isoformat()}"
            f"{'' if apply else ' (dry run)'}")
        out(f"eligible {counts['eligible']}, already notified {counts['already_notified']}, "
            f"skipped unverified {counts['skipped_unverified']}")
        if not apply:
            counts["would_send"] = len(pending)
            out(f"would send {len(pending)}")
            out(f"pending {len(pending)}")
            return counts
        interval = 60.0 / max(1, per_minute)
        for index, recipient in enumerate(pending):
            if index:
                sleep(interval)
            msg = build_notice(given_name=recipient.given_name, to=recipient.email,
                               effective_from=effective_from, site_url=site_url,
                               mail_domain=settings.mail_domain)
            try:
                send(msg, recipient.email)
            except Exception as exc:  # recorded as pending; a rerun retries
                counts["failed"] += 1
                logger.warning("terms notice for user %s failed: %s", recipient.user_id, type(exc).__name__)
                continue
            _record(db, recipient.user_id, datetime.now(timezone.utc))
            counts["sent"] += 1
        out(f"sent {counts['sent']}, failed {counts['failed']}")
        out(f"pending {counts['failed']}")
        return counts
    finally:
        if lock is not None:
            lock.release()


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError("expected YYYY-MM-DD")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--effective-from", type=_parse_date,
                        default=os.environ.get("NEXT_PUBLIC_TERMS_EFFECTIVE_FROM") or None,
                        help="date the terms take effect (YYYY-MM-DD)")
    parser.add_argument("--apply", action="store_true", help="send; without it only count")
    parser.add_argument("--per-minute", type=int, default=30, help="send rate (default 30)")
    parser.add_argument("--site-url", default=os.environ.get("SUPPORT_SITE_URL") or "https://computor.at")
    parser.add_argument("--allow-short-notice", action="store_true",
                        help="send although fewer than 30 days remain (late recipients only)")
    args = parser.parse_args(argv)
    if args.effective_from is None:
        parser.error("--effective-from is required")
    if isinstance(args.effective_from, str):
        args.effective_from = _parse_date(args.effective_from)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    from computor_backend.database import get_db_session

    with get_db_session() as db:
        counts = run(db, effective_from=args.effective_from, apply=args.apply,
                     site_url=args.site_url, settings=get_support_settings(),
                     per_minute=args.per_minute, allow_short_notice=args.allow_short_notice)
    return 1 if counts.get("failed") else 0


if __name__ == "__main__":
    sys.exit(main())
