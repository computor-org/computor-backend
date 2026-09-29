"""First SSO login: linking a new Keycloak identity to an existing user by email.

``handle_sso_callback`` hands a first-time identity the existing Computor
account that owns its email. That is only safe when the IdP vouches for the
address (``email_verified``); otherwise an unverified address in a token
would take the account over.

Live-Postgres tests on a rolled-back outer transaction (same pattern as
test_public_course_registration.py), because the email lookup is
case-insensitive SQL and the one-user-per-email rule is a DB trigger.
Provider, Redis, login cap and git provisioning are stubbed. Skips when
Postgres is unreachable.
"""

import os
import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from computor_backend.business_logic import auth as auth_bl
from computor_backend.exceptions import ForbiddenException
from computor_backend.model.auth import Account, User
from computor_backend.plugins import AuthResult, AuthStatus, UserInfo


def _database_url() -> str:
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "postgres_secret")
    db = os.environ.get("POSTGRES_DB", "computor")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


@pytest.fixture
def db():
    """Session bound to an outer transaction that is always rolled back."""
    try:
        engine = create_engine(_database_url())
        conn = engine.connect()
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"Postgres not reachable: {exc}")
    trans = conn.begin()
    session = sessionmaker(bind=conn)()
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        conn.close()


class _FakeRedis:
    async def set(self, *args, **kwargs):
        return True


@pytest.fixture
def login_as(monkeypatch):
    """Run handle_sso_callback for an identity carrying the given claims."""

    async def _noop(*args, **kwargs):
        return None

    async def _redis():
        return _FakeRedis()

    monkeypatch.setattr(auth_bl, "get_redis_client", _redis)
    monkeypatch.setattr(auth_bl, "enforce_login_cap", _noop)
    monkeypatch.setattr(auth_bl, "touch_login_seat", _noop)
    monkeypatch.setattr(auth_bl, "login_idle_seconds", lambda db: 60)
    monkeypatch.setattr(auth_bl, "_provision_git_server_account", _noop)

    async def _run(db, *, email: str, email_verified, sub: str | None = None):
        attributes = {} if email_verified is None else {"email_verified": email_verified}
        result = AuthResult(
            status=AuthStatus.SUCCESS,
            user_info=UserInfo(
                provider_id=sub or f"kc-{uuid.uuid4().hex}",
                email=email,
                username=email.split("@")[0],
                given_name="Sso",
                family_name="Tester",
                attributes=attributes,
            ),
        )

        async def _ready(provider):
            return object()

        async def _callback(provider, code, state, callback_url):
            return result

        registry = SimpleNamespace(
            ensure_plugin_ready=_ready,
            handle_callback=_callback,
            get_plugin_metadata=lambda provider: SimpleNamespace(
                provider_type=SimpleNamespace(value="oidc")
            ),
        )
        monkeypatch.setattr(auth_bl, "get_plugin_registry", lambda: registry)
        return await auth_bl.handle_sso_callback(
            provider="keycloak",
            code="code",
            state="state",
            state_data={},
            callback_url="http://test/callback",
            db=db,
        )

    return _run


def _existing_user(db, email: str) -> User:
    user = User(given_name="Existing", family_name="Person", email=email)
    db.add(user)
    db.flush()
    return user


def _accounts_of(db, user: User) -> int:
    return db.query(Account).filter(Account.user_id == user.id).count()


def _email() -> str:
    return f"victim.{uuid.uuid4().hex[:10]}@test.local"


@pytest.mark.asyncio
async def test_unverified_email_is_not_linked_to_an_existing_user(db, login_as):
    victim = _existing_user(db, _email())

    with pytest.raises(ForbiddenException) as err:
        await login_as(db, email=victim.email.upper(), email_verified=False)

    assert err.value.status_code == 403
    assert "not verified" in str(err.value.detail)
    assert _accounts_of(db, victim) == 0


@pytest.mark.asyncio
async def test_missing_email_verified_claim_counts_as_unverified(db, login_as):
    victim = _existing_user(db, _email())

    with pytest.raises(ForbiddenException):
        await login_as(db, email=victim.email, email_verified=None)

    assert _accounts_of(db, victim) == 0


@pytest.mark.asyncio
async def test_verified_email_links_to_the_existing_user(db, login_as):
    owner = _existing_user(db, _email())

    result = await login_as(db, email=owner.email.upper(), email_verified=True)

    assert result["user_id"] == str(owner.id)
    assert _accounts_of(db, owner) == 1


@pytest.mark.asyncio
async def test_unverified_email_without_an_existing_user_still_signs_up(db, login_as):
    email = _email()

    result = await login_as(db, email=email, email_verified=False)

    assert result["is_new_user"] is True
    created = db.query(User).filter(User.id == result["user_id"]).one()
    assert created.email == email
