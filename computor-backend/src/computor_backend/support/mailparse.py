"""Parse RFC 5322 mail into what the ticket system stores.

Runs only in the backend (support worker). Never raises on malformed input:
undecodable parts degrade to replacement characters, a missing Message-ID is
replaced by a deterministic one derived from the raw bytes, so re-importing
the same mail stays idempotent.
"""
import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email import message_from_bytes, policy
from email.message import EmailMessage
from email.utils import getaddresses, parsedate_to_datetime
from typing import List, Optional, Tuple

from .sanitize import html_to_text, sanitize_html

_MSGID = re.compile(r"<([^<>\s]+)>")
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
MAX_TEXT_CHARS = 500_000


@dataclass
class ParsedAttachment:
    filename: str
    content_type: str
    data: bytes


@dataclass
class ParsedMail:
    message_id: str
    in_reply_to: List[str]
    references: List[str]
    subject: str
    from_name: Optional[str]
    from_address: Optional[str]
    to: List[str]
    cc: List[str]
    envelope_recipients: List[str]
    date: datetime
    text: str
    html: Optional[str]
    attachments: List[ParsedAttachment] = field(default_factory=list)
    auto_submitted: bool = False

    @property
    def thread_ids(self) -> List[str]:
        """Candidate parent Message-IDs, most specific first."""
        seen, out = set(), []
        for mid in list(self.in_reply_to) + list(reversed(self.references)):
            if mid not in seen:
                seen.add(mid)
                out.append(mid)
        return out

    @property
    def all_recipients(self) -> List[str]:
        return list(dict.fromkeys(self.to + self.cc + self.envelope_recipients))


def normalize_message_id(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    found = _MSGID.findall(str(value))
    mid = found[0] if found else str(value).strip().strip("<>").strip()
    mid = _CTRL.sub("", mid)
    return mid[:998] or None


def message_ids(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [m[:998] for m in _MSGID.findall(_CTRL.sub("", str(value)))]


def _header(msg: EmailMessage, name: str) -> str:
    try:
        value = msg.get(name)
    except Exception:  # malformed header: fall back to the raw value
        value = msg.get_all(name, failobj=[None])[0] if hasattr(msg, "get_all") else None
    return _CTRL.sub("", str(value)) if value is not None else ""


def _addresses(msg: EmailMessage, name: str) -> List[Tuple[str, str]]:
    raw_values = []
    for v in msg.get_all(name, failobj=[]) or []:
        try:
            raw_values.append(str(v))
        except Exception:
            continue
    out = []
    for display, addr in getaddresses(raw_values):
        addr = (addr or "").strip().lower()
        if "@" in addr and len(addr) <= 320:
            out.append((_CTRL.sub("", display or "").strip()[:255], addr))
    return out


def _decode_text(part: EmailMessage) -> str:
    try:
        content = part.get_content()
        if isinstance(content, str):
            return content
    except Exception:
        pass
    payload = part.get_payload(decode=True) or b""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")


def _safe_filename(name: Optional[str], index: int) -> str:
    name = _CTRL.sub("", name or "").replace("/", "_").replace("\\", "_").strip()
    return (name or f"attachment-{index}")[:255]


def parse_mail(raw: bytes) -> ParsedMail:
    msg = message_from_bytes(raw, policy=policy.default)

    message_id = normalize_message_id(_header(msg, "Message-ID"))
    if not message_id:
        message_id = f"sha256-{hashlib.sha256(raw).hexdigest()}@computor.invalid"

    subject = _header(msg, "Subject").strip() or "(no subject)"
    from_list = _addresses(msg, "From")
    from_name, from_address = (from_list[0] if from_list else (None, None))

    try:
        date = parsedate_to_datetime(_header(msg, "Date"))
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
    except Exception:
        date = datetime.now(timezone.utc)

    envelope = []
    for name in ("X-Original-To", "Delivered-To"):
        envelope.extend(a for _, a in _addresses(msg, name))

    auto = _header(msg, "Auto-Submitted").strip().lower()
    auto_submitted = bool(auto and auto != "no") or bool(_header(msg, "X-Autoreply"))

    text_parts: List[str] = []
    html_parts: List[str] = []
    attachments: List[ParsedAttachment] = []
    for part in msg.walk():
        if part.is_multipart():
            continue
        ctype = (part.get_content_type() or "application/octet-stream").lower()
        disposition = part.get_content_disposition()
        filename = part.get_filename()
        if disposition != "attachment" and not filename and ctype == "text/plain":
            text_parts.append(_decode_text(part))
        elif disposition != "attachment" and not filename and ctype == "text/html":
            html_parts.append(_decode_text(part))
        else:
            data = part.get_payload(decode=True) or b""
            if ctype == "message/rfc822" and not data:
                payload = part.get_payload()
                if isinstance(payload, list) and payload:
                    data = payload[0].as_bytes()
            attachments.append(ParsedAttachment(
                filename=_safe_filename(filename, len(attachments) + 1),
                content_type=ctype[:255],
                data=data,
            ))

    raw_html = "\n".join(html_parts) if html_parts else None
    text_parts = [t.replace("\r\n", "\n").replace("\r", "\n").strip("\n") for t in text_parts]
    text = "\n\n".join(text_parts) if text_parts else html_to_text(raw_html or "")
    text = _CTRL.sub("", text)[:MAX_TEXT_CHARS]
    html = sanitize_html(raw_html) if raw_html else None

    return ParsedMail(
        message_id=message_id,
        in_reply_to=message_ids(_header(msg, "In-Reply-To")),
        references=message_ids(_header(msg, "References")),
        subject=subject[:998],
        from_name=from_name or None,
        from_address=from_address,
        to=[a for _, a in _addresses(msg, "To")],
        cc=[a for _, a in _addresses(msg, "Cc")],
        envelope_recipients=list(dict.fromkeys(envelope)),
        date=date,
        text=text,
        html=html or None,
        attachments=attachments,
        auto_submitted=auto_submitted,
    )
