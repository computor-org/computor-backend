"""Mail parsing, sanitising and reply composition for support tickets (#520).

Synthetic mail only. No network, no database.
"""
from email import message_from_bytes, policy

import pytest

from computor_backend.support.config import SupportSettings
from computor_backend.support.mailbox import build_reply
from computor_backend.support.mailparse import normalize_message_id, parse_mail
from computor_backend.support.sanitize import html_to_text, sanitize_html


def _mail(headers: str, body: str, ctype: str = "text/plain; charset=utf-8") -> bytes:
    return (headers.strip() + f"\r\nContent-Type: {ctype}\r\n\r\n" + body).encode()


HOSTILE_HTML = """
<html><head><style>body{background:url(https://track.example/x.png)}</style>
<script>alert(1)</script></head>
<body onload="steal()">
<p style="background:url(https://track.example/p)">Hello <b>team</b></p>
<img src="https://track.example/pixel.gif" width=1 height=1>
<img src="cid:logo">
<a href="javascript:alert(1)">bad link</a>
<a href="https://example.org/ok" onclick="x()">good link</a>
<iframe src="https://evil.example"></iframe>
<form action="https://evil.example"><input name=pw></form>
<svg><script>alert(2)</script></svg>
<link rel=stylesheet href="https://track.example/s.css">
<table><tr><td colspan=2 bgcolor=red>cell</td></tr></table>
</body></html>
"""


class TestSanitize:
    def test_no_active_or_remote_content_survives(self):
        out = sanitize_html(HOSTILE_HTML)
        lowered = out.lower()
        for needle in ("<script", "onload", "onclick", "javascript:", "<img", "<iframe",
                       "<form", "<input", "<svg", "<link", "<style", "style=", "track.example",
                       "url(", "bgcolor", "evil.example"):
            assert needle not in lowered, needle
        assert "Hello <b>team</b>" in out
        assert 'href="https://example.org/ok"' in out
        assert 'rel="noopener noreferrer nofollow"' in out
        assert 'colspan="2"' in out

    def test_html_to_text_keeps_lines_and_drops_markup(self):
        text = html_to_text("<p>One &amp; two</p><p>three<br>four</p><script>x()</script>")
        assert text == "One & two\nthree\nfour"


class TestParse:
    def test_plain_mail_headers_and_threading_ids(self):
        raw = _mail(
            """
From: "Ada Reporter" <Ada@Example.org>
To: Contact <contact@computor.at>, other@example.org
Cc: security@computor.at
Subject: =?utf-8?q?Gr=C3=BC=C3=9Fe?=
Message-ID: <abc.123@example.org>
In-Reply-To: <parent@computor.at>
References: <root@example.org> <mid@example.org> <parent@computor.at>
Date: Wed, 21 Oct 2026 10:00:00 +0200
X-Original-To: contact@computor.at
""",
            "Hallo\r\nZeile 2\r\n",
        )
        mail = parse_mail(raw)
        assert mail.message_id == "abc.123@example.org"
        assert mail.subject == "Grüße"
        assert mail.from_address == "ada@example.org"
        assert mail.from_name == "Ada Reporter"
        assert mail.to == ["contact@computor.at", "other@example.org"]
        assert mail.cc == ["security@computor.at"]
        assert mail.envelope_recipients == ["contact@computor.at"]
        # In-Reply-To first, then References newest to oldest, no duplicates.
        assert mail.thread_ids == ["parent@computor.at", "mid@example.org", "root@example.org"]
        assert mail.text == "Hallo\nZeile 2"
        assert mail.html is None
        assert mail.date.utcoffset().total_seconds() == 7200

    def test_missing_message_id_is_deterministic(self):
        raw = _mail("From: a@example.org\r\nTo: contact@computor.at\r\nSubject: x", "body")
        first, second = parse_mail(raw), parse_mail(raw)
        assert first.message_id == second.message_id
        assert first.message_id.endswith("@computor.invalid")
        other = parse_mail(raw + b"!")
        assert other.message_id != first.message_id

    def test_html_only_mail_gets_text_and_sanitised_html(self):
        raw = _mail("From: a@example.org\r\nTo: contact@computor.at\r\nSubject: h\r\nMessage-ID: <h@x>",
                    HOSTILE_HTML, "text/html; charset=utf-8")
        mail = parse_mail(raw)
        assert "Hello team" in mail.text
        assert "alert" not in mail.text
        assert mail.html and "<script" not in mail.html and "track.example" not in mail.html

    def test_multipart_with_attachment_and_bad_charset(self):
        raw = (
            b"From: a@example.org\r\nTo: privacy@computor.at\r\nSubject: att\r\n"
            b"Message-ID: <m@x>\r\nMIME-Version: 1.0\r\n"
            b'Content-Type: multipart/mixed; boundary="B"\r\n\r\n'
            b"--B\r\nContent-Type: text/plain; charset=x-unknown-charset\r\n\r\nhi \xff there\r\n"
            b"--B\r\nContent-Type: text/html; charset=utf-8\r\nContent-Disposition: attachment; filename=\"../../evil.html\"\r\n\r\n"
            b"<script>alert(1)</script>\r\n"
            b"--B\r\nContent-Type: application/pdf; name=r.pdf\r\nContent-Transfer-Encoding: base64\r\n"
            b"Content-Disposition: attachment; filename=r.pdf\r\n\r\nJVBERi0xLjQK\r\n--B--\r\n"
        )
        mail = parse_mail(raw)
        assert "hi" in mail.text and "there" in mail.text
        names = [a.filename for a in mail.attachments]
        # An HTML attachment stays an attachment (never rendered), path stripped.
        assert names == [".._.._evil.html", "r.pdf"]
        assert mail.attachments[1].data == b"%PDF-1.4\n"
        assert mail.html is None

    def test_auto_submitted_flag(self):
        raw = _mail("From: a@example.org\r\nTo: contact@computor.at\r\nSubject: x\r\n"
                    "Auto-Submitted: auto-replied", "away")
        assert parse_mail(raw).auto_submitted is True

    def test_normalize_message_id(self):
        assert normalize_message_id(" <a@b> ") == "a@b"
        assert normalize_message_id("a@b") == "a@b"
        assert normalize_message_id("") is None


class TestReply:
    def _settings(self):
        return SupportSettings(_env_file=None)

    def test_reply_headers(self):
        msg = build_reply(
            self._settings(), sender_name='Jane "Doe"\r\nBcc: x@evil', from_address="contact@computor.at",
            to=["ada@example.org"], subject="Question", body="Answer",
            in_reply_to="abc@example.org", references=["root@example.org"], ticket_number=7,
        )
        parsed = message_from_bytes(msg.as_bytes(), policy=policy.default)
        assert parsed["From"].addresses[0].addr_spec == "contact@computor.at"
        assert parsed["From"].addresses[0].display_name == "Jane Doe Bcc: x@evil via computor.at"
        assert parsed["Bcc"] is None
        assert parsed["Subject"] == "Re: Question"
        assert parsed["In-Reply-To"] == "<abc@example.org>"
        assert parsed["References"] == "<root@example.org> <abc@example.org>"
        assert parsed["Message-ID"].endswith("@computor.at>")
        assert parsed.get_content().strip() == "Answer"

    def test_reply_sender_must_be_team_address(self):
        with pytest.raises(ValueError):
            build_reply(self._settings(), sender_name="X", from_address="noreply@computor.at",
                        to=["a@example.org"], subject="s", body="b", in_reply_to=None,
                        references=[], ticket_number=1)

    def test_existing_re_prefix_not_doubled(self):
        msg = build_reply(self._settings(), sender_name="", from_address="abuse@computor.at",
                          to=["a@example.org"], subject="RE: hi", body="b", in_reply_to=None,
                          references=[], ticket_number=1)
        assert msg["Subject"] == "RE: hi"
        assert str(msg["From"]) == '"via computor.at" <abuse@computor.at>'


class TestWelcomeMail:
    def _settings(self, **kw):
        return SupportSettings(welcome_mail_enabled=True, mail_enabled=True, **kw)

    @pytest.mark.parametrize("language", ["de", "en", "fr"])
    def test_localized_text_with_name_and_link(self, language):
        from computor_backend.support.welcome import build_welcome

        msg = build_welcome(self._settings(site_url="https://example.test/"),
                            given_name="  Ada  ", to="ada@example.org", language=language)
        body = msg.get_content()
        assert msg["To"] == "ada@example.org"
        assert "contact@computor.at" in msg["From"]
        assert msg["Auto-Submitted"] == "auto-generated"
        german = language == "de"
        assert body.startswith("Hallo Ada," if german else "Hello Ada,")
        assert ("Hello Ada," not in body) if german else ("Hallo Ada," not in body)
        assert msg["Subject"] == ("Willkommen bei computor.at" if german else "Welcome to computor.at")
        assert "https://example.test " in body and "//example.test/" not in body
        # One step, in the labels the web interface shows.
        assert ("im Kurskatalog" if german else "in the course catalog") in body
        assert ("öffne ihn dort in VS Code" if german else 'open it in VS Code from there') in body

    def test_sender_must_be_a_team_address(self):
        from computor_backend.support.welcome import build_welcome

        with pytest.raises(ValueError):
            build_welcome(self._settings(welcome_from="someone@example.org"),
                          given_name="Ada", to="ada@example.org")

    def test_disabled_deployment_sends_nothing(self, monkeypatch):
        from computor_backend.support import mailbox, welcome

        sent = []
        monkeypatch.setattr(mailbox, "smtp_send", lambda *a, **k: sent.append(a))
        assert welcome.send_welcome("any", SupportSettings())["state"] == "disabled"
        assert sent == []

    @pytest.mark.parametrize("starttls", [True, False])
    def test_smtp_login_is_skipped_without_credentials(self, monkeypatch, starttls):
        from computor_backend.support import mailbox

        calls = []

        class _Smtp:
            def __init__(self, *a, **k): pass
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def ehlo(self): calls.append("ehlo")
            def starttls(self, context=None): calls.append("starttls")
            def login(self, *a): calls.append("login")
            def send_message(self, *a, **k): calls.append("send")

        monkeypatch.setattr(mailbox.smtplib, "SMTP", _Smtp)
        mailbox.smtp_send(SupportSettings(smtp_starttls=starttls), object(), "contact@computor.at", ["a@example.org"])
        assert calls == (["ehlo", "starttls", "ehlo", "send"] if starttls else ["ehlo", "send"])
        calls.clear()
        mailbox.smtp_send(SupportSettings(smtp_user="u", smtp_password="p", smtp_starttls=starttls), object(),
                          "contact@computor.at", ["a@example.org"])
        assert "login" in calls


@pytest.mark.asyncio
@pytest.mark.parametrize("imports", [True, False])
async def test_welcome_only_worker_can_disable_mailbox_imports(monkeypatch, imports):
    from computor_backend.support import config
    from computor_backend.tasks import temporal_support_mail
    from computor_backend.tasks.temporal_worker import TemporalWorker

    calls = []

    async def ensure_schedule(client, interval):
        calls.append((client, interval))

    settings = SupportSettings(mail_enabled=True, welcome_mail_enabled=True, mail_import_enabled=imports)
    monkeypatch.setattr(config, "get_support_settings", lambda: settings)
    monkeypatch.setattr(temporal_support_mail, "ensure_import_schedule", ensure_schedule)
    worker = TemporalWorker(task_queues=["support"])
    worker.client = object()
    await worker._ensure_support_schedule()
    assert calls == ([(worker.client, settings.mail_poll_seconds)] if imports else [])
