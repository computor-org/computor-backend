"""Welcome mail after a completed registration (issues#185).

The mail is queued once, when the first verified login has created the
Computor user (``business_logic.auth.handle_sso_callback``). It is sent by the
support worker, the only process with SMTP access, and is best effort: it is
never retried, so a user cannot receive it twice.
"""
import logging
from email.message import EmailMessage
from email.policy import SMTP as SMTP_POLICY
from email.utils import format_datetime, formataddr, make_msgid
from datetime import datetime, timezone
from typing import Dict

from . import mailbox
from .config import SupportSettings, get_support_settings

logger = logging.getLogger(__name__)

SUBJECT = {"de": "Willkommen bei computor.at", "en": "Welcome to computor.at"}

_DE = """Hallo {name},

deine Registrierung bei computor.at ist abgeschlossen. So kommst du zu deiner ersten Aufgabe:

1. Melde dich unter {url} an und wähle in der Kursliste "Kurs beitreten".
2. Öffne den Kurs und klicke auf "Arbeitsumgebung starten". Die Arbeitsumgebung öffnet sich in einem neuen Tab und ist nach kurzer Zeit bereit.
3. Wähle eine Aufgabe, teste sie mit dem Reagenzglas-Symbol und gib sie mit dem Wolken-Symbol ab.

Bei Fragen antworte einfach auf diese Nachricht.
"""

_EN = """Hello {name},

your registration at computor.at is complete. This is how you get to your first assignment:

1. Sign in at {url} and choose "Join course" in the course list.
2. Open the course and click "Launch workspace". The workspace opens in a new tab and is ready after a short while.
3. Pick an assignment, test it with the beaker icon and submit it with the cloud icon.

If you have questions, just reply to this message.
"""


def build_welcome(settings: SupportSettings, *, given_name: str, to: str, language: str = "en") -> EmailMessage:
    """Use the registration language, with English as the fallback."""
    language = language if language in SUBJECT else "en"
    sender = settings.welcome_from.strip().lower()
    if sender not in settings.team_address_list:
        raise ValueError(f"sender {sender!r} is not a team address")
    name = " ".join((given_name or "").split()) or "und willkommen"
    name_en = " ".join((given_name or "").split()) or "and welcome"
    url = settings.site_url.rstrip("/")
    msg = EmailMessage(policy=SMTP_POLICY)
    msg["From"] = formataddr(("computor.at", sender))
    msg["To"] = to
    msg["Subject"] = SUBJECT[language]
    msg["Date"] = format_datetime(datetime.now(timezone.utc))
    msg["Message-ID"] = make_msgid(idstring="welcome", domain=settings.mail_domain)
    msg["Auto-Submitted"] = "auto-generated"
    msg.set_content(_DE.format(name=name, url=url) if language == "de" else _EN.format(name=name_en, url=url))
    return msg


def send_welcome(user_id: str, settings: SupportSettings | None = None, *, language: str = "en") -> Dict[str, str]:
    """Send the welcome mail to one user. Name and address are read from the
    database, so no personal data travels through the workflow parameters."""
    from computor_backend.database import get_db_session
    from computor_backend.model.auth import User

    settings = settings or get_support_settings()
    if not (settings.mail_enabled and settings.welcome_mail_enabled):
        return {"state": "disabled"}
    with get_db_session() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if user is None or not user.email or user.banned_at is not None:
            return {"state": "skipped"}
        email, given_name = user.email, user.given_name or ""
    try:
        msg = build_welcome(settings, given_name=given_name, to=email, language=language)
        mailbox.smtp_send(settings, msg, settings.welcome_from.strip().lower(), [email])
    except Exception as exc:
        logger.exception("welcome mail for user %s: send failed", user_id)
        return {"state": "failed", "error": f"{type(exc).__name__}"}
    return {"state": "sent"}
