"""A first sign-in leaves the new account on Automatic unless the choice was explicit.

``ui_locales`` at login is the *resolved* interface language of the web app, so
it is derived from the browser whenever the visitor never chose anything.
Storing it as the profile language made every new account explicit and killed
"Automatic (browser)" (computor-org/issues#534). The web app now marks a real
signed-out choice with ``explicit_language=1`` in the login state, and only that
one is stored; ``ui_locales`` still picks the language of the welcome mail.

Live-Postgres tests on a rolled-back outer transaction, like
``test_sync_course_metadata.py``. Skips when Postgres is unreachable.
"""

import os
import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from computor_backend.business_logic import auth as auth_bl
from computor_backend.model.auth import Profile
from computor_backend.model.language import Language
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


@pytest.fixture
def registration_languages(db):
    # Production migrations seed these reference rows; create_all does not.
    for code, name in (("de", "German"), ("en", "English")):
        if db.get(Language, code) is None:
            db.add(Language(code=code, name=name))
    db.flush()


class _FakeRedis:
    async def set(self, *args, **kwargs):
        return True


@pytest.fixture
def sign_up(monkeypatch):
    """Run a first SSO sign-in for a fresh identity with the given login state."""

    async def _noop(*args, **kwargs):
        return None

    async def _redis():
        return _FakeRedis()

    monkeypatch.setattr(auth_bl, "get_redis_client", _redis)
    monkeypatch.setattr(auth_bl, "enforce_login_cap", _noop)
    monkeypatch.setattr(auth_bl, "touch_login_seat", _noop)
    monkeypatch.setattr(auth_bl, "login_idle_seconds", lambda db: 60)
    monkeypatch.setattr(auth_bl, "_provision_git_server_account", _noop)

    async def _run(db, *, language: str | None, explicit: bool = False):
        email = f"signup.{uuid.uuid4().hex[:10]}@test.local"
        result = AuthResult(
            status=AuthStatus.SUCCESS,
            user_info=UserInfo(
                provider_id=f"kc-{uuid.uuid4().hex}",
                email=email,
                username=email.split("@")[0],
                given_name="New",
                family_name="Student",
                attributes={"email_verified": True},
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

        state_data = {} if language is None else {"ui_locales": language}
        if explicit:
            state_data["explicit_language"] = "1"
        signed_in = await auth_bl.handle_sso_callback(
            provider="keycloak",
            code="code",
            state="state",
            state_data=state_data,
            callback_url="http://test/callback",
            db=db,
        )
        return email, signed_in

    return _run


def _profile_of(db, user_id: str) -> Profile | None:
    return db.query(Profile).filter(Profile.user_id == user_id).first()


@pytest.mark.asyncio
@pytest.mark.parametrize("language", ["de", "en"])
async def test_first_login_without_the_explicit_flag_leaves_the_account_automatic(
    db, sign_up, registration_languages, language
):
    """The browser-derived language stays a display hint, not a profile choice."""
    _, signed_in = await sign_up(db, language=language)

    assert signed_in["is_new_user"] is True
    profile = _profile_of(db, signed_in["user_id"])
    assert profile is None or profile.language_code is None


@pytest.mark.asyncio
@pytest.mark.parametrize("language", ["de", "en"])
async def test_first_login_with_the_explicit_flag_stores_that_language(
    db, sign_up, registration_languages, language
):
    _, signed_in = await sign_up(db, language=language, explicit=True)

    profile = _profile_of(db, signed_in["user_id"])
    assert profile is not None
    assert profile.language_code == language


@pytest.mark.asyncio
async def test_the_welcome_mail_still_follows_ui_locales_without_the_flag(
    db, sign_up, registration_languages, monkeypatch
):
    """Dropping the profile write must not cost the welcome mail its language."""
    from computor_backend import tasks as tasks_pkg
    from computor_backend.support import config as support_config

    submitted = []

    class _Executor:
        async def submit_task(self, submission):
            submitted.append(submission)

    monkeypatch.setattr(tasks_pkg, "get_task_executor", lambda: _Executor())
    monkeypatch.setattr(
        support_config,
        "get_support_settings",
        lambda: support_config.SupportSettings(welcome_mail_enabled=True),
    )

    _, signed_in = await sign_up(db, language="de")

    assert [(t.task_name, t.parameters["language"]) for t in submitted] == [
        ("support_welcome_mail", "de")
    ]
