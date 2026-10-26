"""Terms 1.6 notice email: content, recipient selection, dry run, idempotence.

The database tests use synthetic rows in a transaction that is rolled back,
and skip when Postgres is unreachable (as test_support_tickets_db.py).
"""
import os
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from computor_backend.support import terms_notice
from computor_backend.support.config import SupportSettings

NOW = datetime(2026, 11, 2, 9, 0, tzinfo=timezone.utc)
EFFECTIVE = date(2026, 12, 7)
SETTINGS = SupportSettings(_env_file=None, mail_enabled=True)


def test_notice_is_german_first_then_english_with_date_and_links():
    msg = terms_notice.build_notice(given_name="Anna", to="anna@test.local",
                                    effective_from=EFFECTIVE, site_url="https://computor.at/")
    body = msg.get_content()
    assert msg["Subject"] == ("computor.at: neue Nutzungsbedingungen ab 07.12.2026 / "
                              "new Terms of Use from 7 December 2026")
    assert msg["From"].endswith("<contact@computor.at>")
    assert msg["Auto-Submitted"] == "auto-generated"
    de, en = body.split("\n---\n")
    assert de.startswith("Hallo Anna,") and "ab 07.12.2026 gelten" in de
    assert en.lstrip().startswith("Hello Anna,") and "from 7 December 2026" in en
    for part, changes, privacy in ((de, "/terms/changes", "/privacy\n"), (en, "/terms/en/changes", "/privacy/en\n")):
        assert f"https://computor.at{changes}" in part
        assert f"https://computor.at{privacy}" in part
        assert terms_notice.OLD_VERSION_URL in part
        assert "privacy@computor.at" in part
        lines = [line for line in part.strip().splitlines() if line]
        assert len(lines) <= 9, lines  # greeting + at most 8 lines


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
    """One user per selection case; returns name -> email."""
    from computor_backend.model.auth import Account, User

    suffix = uuid.uuid4().hex[:8]
    created = NOW - timedelta(days=20)

    def user(name, *, verified=True, **fields):
        email = f"{name}.{suffix}@test.local"
        row = User(given_name=name.title(), family_name="Synthetic", email=email,
                   created_at=fields.pop("created_at", created), **fields)
        db.add(row)
        db.flush()
        if verified is not None:
            db.add(Account(provider="keycloak", type="oidc", provider_account_id=f"kc-{uuid.uuid4().hex}",
                           user_id=row.id, builtin=True,
                           properties={"email": email, "attributes": {"email_verified": verified}}))
        return email

    emails = {
        "anna": user("anna"),
        "banned": user("banned", banned_at=NOW - timedelta(days=1)),
        "unverified": user("unverified", verified=False),
        "noaccount": user("noaccount", verified=None),
        "service": user("service", is_service=True),
        "archived": user("archived", archived_at=NOW - timedelta(days=1)),
        "newer": user("newer", created_at=NOW + timedelta(minutes=5)),
    }
    db.flush()
    return emails


def _run(db, sent, *, apply, fail=(), **kw):
    def send(msg, rcpt):
        if rcpt in fail:
            raise OSError("relay refused")
        sent.append(rcpt)

    lines = []
    counts = terms_notice.run(db, effective_from=EFFECTIVE, apply=apply, site_url="https://computor.at",
                              settings=SETTINGS, now=NOW, send=send, sleep=lambda s: None,
                              out=lines.append, **kw)
    return counts, lines


def _mine(sent, people):
    return sorted(e for e in sent if e in people.values())


def test_recipients_are_verified_live_accounts_only(db, people):
    found = terms_notice.select(db, NOW)
    pending = {r.email for r in found["pending"]}
    assert {people["anna"], people["banned"]} <= pending
    for name in ("unverified", "noaccount", "service", "archived", "newer"):
        assert people[name] not in pending, name


def test_dry_run_counts_and_sends_nothing(db, people):
    sent = []
    counts, lines = _run(db, sent, apply=False)
    assert sent == []
    assert counts["would_send"] >= 2 and f"pending {counts['would_send']}" in lines
    assert not any("@" in line for line in lines)  # counts only, no addresses
    assert {people["anna"], people["banned"]} <= {r.email for r in terms_notice.select(db, NOW)["pending"]}


def test_apply_sends_once_and_a_rerun_sends_nothing(db, people):
    sent = []
    first, _ = _run(db, sent, apply=True)
    assert _mine(sent, people) == sorted([people["anna"], people["banned"]])
    assert first["failed"] == 0 and first["sent"] == len(sent)
    again = []
    second, lines = _run(db, again, apply=True)
    assert again == [] and second["sent"] == 0
    assert "pending 0" in lines
    _, dry = _run(db, [], apply=False)
    assert "would send 0" in dry


def test_failed_recipient_stays_pending_and_is_retried_alone(db, people):
    sent = []
    counts, lines = _run(db, sent, apply=True, fail={people["banned"]})
    assert counts["failed"] == 1 and "pending 1" in lines
    retry = []
    _run(db, retry, apply=True)
    assert retry == [people["banned"]]


def test_refuses_short_notice_and_missing_smtp(db, people):
    with pytest.raises(SystemExit, match="at least 30"):
        terms_notice.run(db, effective_from=NOW.date() + timedelta(days=29), apply=True,
                         site_url="x", settings=SETTINGS, now=NOW, send=lambda m, r: None)
    with pytest.raises(SystemExit, match="SUPPORT_MAIL_ENABLED"):
        terms_notice.run(db, effective_from=EFFECTIVE, apply=True, site_url="x",
                         settings=SupportSettings(_env_file=None), now=NOW, send=lambda m, r: None)
