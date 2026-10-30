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
from computor_backend.model.auth import Account, Profile, User
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

    async def _run(
        db,
        *,
        email: str,
        email_verified,
        sub: str | None = None,
        language: str | None = None,
        explicit: bool = False,
    ):
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
        state_data = {"ui_locales": language} if language else {}
        if explicit:
            state_data["explicit_language"] = "1"
        return await auth_bl.handle_sso_callback(
            provider="keycloak",
            code="code",
            state="state",
            state_data=state_data,
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
    assert "verify your email address first" in str(err.value.detail)
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
async def test_unverified_email_cannot_create_a_user_either(db, login_as):
    email = _email()

    with pytest.raises(ForbiddenException) as err:
        await login_as(db, email=email, email_verified=False)

    assert "verify your email address first" in str(err.value.detail)
    assert db.query(User).filter(User.email == email).count() == 0


@pytest.mark.asyncio
async def test_verified_email_without_an_existing_user_signs_up(db, login_as):
    email = _email()

    result = await login_as(db, email=email, email_verified=True)

    assert result["is_new_user"] is True
    created = db.query(User).filter(User.id == result["user_id"]).one()
    assert created.email == email


@pytest.mark.asyncio
async def test_a_returning_identity_is_not_rechecked(db, login_as):
    """The guard is for first logins; an existing Account keeps working."""
    sub = f"kc-{uuid.uuid4().hex}"
    first = await login_as(db, email=_email(), email_verified=True, sub=sub)

    again = await login_as(db, email=_email(), email_verified=False, sub=sub)

    assert again["user_id"] == first["user_id"]
    assert again["is_new_user"] is False


@pytest.mark.asyncio
async def test_a_returning_login_keeps_the_stored_clone_tokens(db, login_as):
    """A login refreshes the identity claims, not the whole properties blob.

    The OIDC account also holds the encrypted Forgejo clone tokens. Replacing
    the blob on every login dropped them, so the next provisioning re-minted the
    workspace token and revoked the one in every existing clone's remote
    (computor-org/issues#332, #433).
    """
    sub = f"kc-{uuid.uuid4().hex}"
    await login_as(db, email=_email(), email_verified=True, sub=sub)
    account = db.query(Account).filter(Account.provider_account_id == sub).one()
    stored = {
        "forgejo_clone_tokens": {"srv-1": "gAAAAA-workspace"},
        "forgejo_personal_clone_tokens": {"srv-1": "gAAAAA-cli"},
    }
    account.properties = {**account.properties, **stored}
    db.flush()

    new_email = _email()
    await login_as(db, email=new_email, email_verified=True, sub=sub)

    db.refresh(account)
    assert account.properties["forgejo_clone_tokens"] == stored["forgejo_clone_tokens"]
    assert (
        account.properties["forgejo_personal_clone_tokens"]
        == stored["forgejo_personal_clone_tokens"]
    )
    # The identity claims themselves are still refreshed from the token.
    assert account.properties["email"] == new_email
    assert account.properties["username"] == new_email.split("@")[0]


@pytest.mark.asyncio
async def test_unverified_claim_cannot_capture_a_later_staff_import(db, login_as, monkeypatch):
    """Signup with someone else's unverified email, then staff import that email.

    Before the fix the signup created a User owning the victim's address, and
    the import (which resolves users by email) enrolled the attacker in the
    victim's private course.
    """
    from sqlalchemy_utils import Ltree

    import computor_backend.business_logic.course_member_post_create as hook_mod
    from computor_backend.business_logic.course_member_import import import_course_member
    from computor_backend.model.course import Course, CourseFamily
    from computor_backend.model.organization import Organization
    from computor_backend.permissions.principal import Principal
    from computor_types.course_member_import import CourseMemberImportRequest

    async def _no_external_services(*args, **kwargs):
        return None

    monkeypatch.setattr(hook_mod, "course_member_post_create", _no_external_services)

    victim_email = _email()
    attacker_sub = f"attacker-{uuid.uuid4().hex}"
    with pytest.raises(ForbiddenException):
        await login_as(db, email=victim_email, email_verified=False, sub=attacker_sub)

    tag = f"ssoimport_{uuid.uuid4().hex[:10]}"
    org = Organization(
        title="Import Org", organization_type="organization", path=Ltree(tag), properties={}
    )
    db.add(org)
    db.flush()
    family = CourseFamily(title="Family", path=Ltree(f"{tag}.family"), organization_id=org.id)
    db.add(family)
    db.flush()
    course = Course(
        title="Private",
        path=Ltree(f"{tag}.family.private"),
        course_family_id=family.id,
        organization_id=org.id,
        public=False,
    )
    staff = User(given_name="Staff", family_name="Member", email=f"staff.{tag}@test.local")
    db.add_all([course, staff])
    db.flush()

    result = await import_course_member(
        course.id,
        CourseMemberImportRequest(
            email=victim_email,
            given_name="Intended",
            family_name="Victim",
            course_role_id="_student",
            course_group_title="Class",
        ),
        Principal(user_id=str(staff.id), is_admin=True, roles=["_admin"]),
        db,
    )

    assert result.success, result.message
    enrolled = db.query(User).filter(User.id == result.course_member["user_id"]).one()
    attacker_accounts = db.query(Account).filter(
        Account.provider_account_id == attacker_sub
    )
    assert attacker_accounts.count() == 0
    assert enrolled.given_name == "Intended"


def test_audit_counts_users_whose_sso_email_was_never_verified(db):
    from computor_backend.scripts.audit_unverified_sso_users import audit

    before = audit(db)

    def _sso_user(flag):
        user = _existing_user(db, _email())
        attributes = {} if flag is None else {"email_verified": flag}
        db.add(
            Account(
                provider="keycloak",
                type="oidc",
                provider_account_id=f"kc-{uuid.uuid4().hex}",
                user_id=user.id,
                builtin=True,
                properties={"email": user.email, "attributes": attributes},
            )
        )
        db.flush()

    _sso_user(True)
    _sso_user(False)
    _sso_user(None)
    # Verified, but for a different address than User.email.
    other = _existing_user(db, _email())
    db.add(
        Account(
            provider="keycloak",
            type="oidc",
            provider_account_id=f"kc-{uuid.uuid4().hex}",
            user_id=other.id,
            builtin=True,
            properties={"email": _email(), "attributes": {"email_verified": True}},
        )
    )
    db.flush()
    after = audit(db)

    assert after["unverified_verified_other_email"] - before["unverified_verified_other_email"] == 1
    assert after["sso_users_with_email"] - before["sso_users_with_email"] == 4
    assert after["unverified_total"] - before["unverified_total"] == 3
    assert after["unverified_email_verified_false"] - before["unverified_email_verified_false"] == 1
    assert after["unverified_claim_missing"] - before["unverified_claim_missing"] == 1


@pytest.mark.asyncio
async def test_a_pre_fix_reservation_stays_flagged_after_a_verified_login_elsewhere(
    db, login_as, caplog
):
    """Legacy state: an identity reserved someone else's unverified address as
    User.email (possible before the first-login check). Logging in later with
    its *own* verified address must neither rewrite User.email silently nor
    make the audit treat the reserved address as verified.
    """
    from computor_backend.scripts.audit_unverified_sso_users import audit

    before = audit(db)
    victim_email = _email()
    sub = f"legacy-{uuid.uuid4().hex}"
    squatter = _existing_user(db, victim_email)
    db.add(
        Account(
            provider="keycloak",
            type="oidc",
            provider_account_id=sub,
            user_id=squatter.id,
            builtin=True,
            properties={"email": victim_email, "attributes": {"email_verified": False}},
        )
    )
    db.flush()

    with caplog.at_level("WARNING"):
        result = await login_as(db, email=_email(), email_verified=True, sub=sub)

    assert result["user_id"] == str(squatter.id)
    db.refresh(squatter)
    assert squatter.email == victim_email
    assert "differs from User.email" in caplog.text
    after = audit(db)
    assert after["unverified_total"] - before["unverified_total"] == 1
    assert after["unverified_verified_other_email"] - before["unverified_verified_other_email"] == 1


@pytest.fixture
def welcome_queue(monkeypatch):
    """Record the tasks the login queues, with the welcome mail switched on."""
    from computor_backend import tasks as tasks_pkg
    from computor_backend.support import config as support_config

    submitted = []

    class _Executor:
        async def submit_task(self, submission):
            submitted.append(submission)

    monkeypatch.setattr(tasks_pkg, "get_task_executor", lambda: _Executor())
    monkeypatch.setattr(
        support_config, "get_support_settings",
        lambda: support_config.SupportSettings(welcome_mail_enabled=True),
    )
    return submitted


@pytest.mark.asyncio
@pytest.mark.parametrize("language", ["de", "en", None])
async def test_completed_registration_queues_one_welcome_mail(db, login_as, welcome_queue, registration_languages, language):
    sub = f"kc-{uuid.uuid4().hex}"
    first = await login_as(db, email=_email(), email_verified=True, sub=sub, language=language)

    assert [(t.task_name, t.queue, t.workflow_id, t.parameters) for t in welcome_queue] == [
        ("support_welcome_mail", "support", f"support-welcome-{first['user_id']}",
         {"user_id": first["user_id"], "language": language or "en"}),
    ]

    await login_as(db, email=_email(), email_verified=True, sub=sub)
    assert len(welcome_queue) == 1


@pytest.mark.asyncio
async def test_refused_unverified_registration_sends_no_welcome_mail(db, login_as, welcome_queue):
    with pytest.raises(ForbiddenException):
        await login_as(db, email=_email(), email_verified=False)

    assert welcome_queue == []


@pytest.mark.asyncio
async def test_welcome_mail_is_off_unless_enabled(db, login_as, welcome_queue, monkeypatch):
    from computor_backend.support import config as support_config

    monkeypatch.setattr(support_config, "get_support_settings", lambda: support_config.SupportSettings())
    await login_as(db, email=_email(), email_verified=True)

    assert welcome_queue == []


@pytest.mark.asyncio
async def test_an_unreachable_queue_does_not_fail_the_login(db, login_as, welcome_queue, monkeypatch):
    from computor_backend import tasks as tasks_pkg

    class _Down:
        async def submit_task(self, submission):
            raise ConnectionError("temporal is down")

    monkeypatch.setattr(tasks_pkg, "get_task_executor", lambda: _Down())
    result = await login_as(db, email=_email(), email_verified=True)

    assert result["is_new_user"] is True


@pytest.fixture
def registration_languages(db):
    # Production migrations seed these reference rows; create_all does not.
    for code, name in (("de", "German"), ("en", "English")):
        if db.get(Language, code) is None:
            db.add(Language(code=code, name=name))
    db.flush()


@pytest.mark.asyncio
@pytest.mark.parametrize("language", ["de", "en"])
async def test_registration_persists_explicit_profile_language(db, login_as, registration_languages, language):
    """Only a choice marked explicit at login becomes the profile language.

    Before, any ``ui_locales`` was stored, which is the browser-derived language
    and left no new account on Automatic (computor-org/issues#534).
    """
    result = await login_as(db, email=_email(), email_verified=True, language=language, explicit=True)

    profile = db.query(Profile).filter(Profile.user_id == result["user_id"]).one()
    assert profile.language_code == language


@pytest.mark.asyncio
@pytest.mark.parametrize("language", [None, "fr", "invalid"])
async def test_registration_does_not_persist_an_unsupported_profile_language(db, login_as, language):
    result = await login_as(db, email=_email(), email_verified=True, language=language, explicit=True)

    profile = db.query(Profile).filter(Profile.user_id == result["user_id"]).first()
    assert profile is None or profile.language_code is None


@pytest.mark.asyncio
@pytest.mark.parametrize("stored_language", ["de", None])
async def test_returning_login_preserves_profile_language(db, login_as, registration_languages, stored_language):
    sub = f"kc-{uuid.uuid4().hex}"
    first = await login_as(db, email=_email(), email_verified=True, sub=sub)
    profile = db.query(Profile).filter(Profile.user_id == first["user_id"]).first()
    if profile is None:
        profile = Profile(user_id=first["user_id"])
        db.add(profile)
    profile.language_code = stored_language
    db.flush()

    await login_as(db, email=_email(), email_verified=True, sub=sub, language="en")

    db.refresh(profile)
    assert profile.language_code == stored_language
