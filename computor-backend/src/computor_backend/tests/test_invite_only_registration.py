"""Invite-only registration with a hard user cap (public pilot).

Live-Postgres tests that drive the real first-login path,
``business_logic.auth.handle_sso_callback``, with only the outside world
faked: the OIDC provider (it returns the identity we choose), Redis, git
provisioning and the Keycloak admin API. The oracle is the database — does a
``user`` row exist afterwards, what is the invite's ``use_count``, who is
recorded as referrer — plus what the fake Keycloak admin was asked to delete.

Rows are committed (the gate takes row locks and the refusal path rolls the
session back, neither of which a rollback-wrapped fixture survives), so every
test cleans up after itself and restores the ``instance_settings`` singleton.
Skips when Postgres is unreachable.
"""

import asyncio
import os
import threading
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import computor_backend.business_logic.auth as auth_mod
from computor_backend.business_logic.auth import handle_sso_callback
from computor_backend.business_logic.registration_admission import (
    RegistrationRefused,
    count_registered_users,
    ensure_referral_invites,
    invite_public_status,
)
from computor_backend.model.auth import User
from computor_backend.model.instance import InstanceSettings
from computor_backend.model.invite import InviteLink
from computor_backend.model.role import UserRole
from computor_backend.plugins import AuthStatus
from computor_backend.plugins.base import AuthResult, UserInfo


def _database_url() -> str:
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "postgres_secret")
    db = os.environ.get("POSTGRES_DB", "computor")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


class _FakeRedis:
    def __init__(self):
        self.data = {}

    async def set(self, key, value, ex=None):
        self.data[key] = value

    async def get(self, key):
        return self.data.get(key)

    async def delete(self, key):
        self.data.pop(key, None)


class _FakeRegistry:
    """The OIDC provider: returns whichever identity the test put in ``next``."""

    def __init__(self):
        self.identities = {}

    async def ensure_plugin_ready(self, provider):
        return object()

    async def handle_callback(self, provider, code, state, callback_url):
        return AuthResult(
            status=AuthStatus.SUCCESS,
            user_info=self.identities[code],
            session_data={"id_token": f"idtoken-{code}"},
        )

    def get_plugin_metadata(self, provider):
        return SimpleNamespace(provider_type=SimpleNamespace(value="oidc"))


class _FakeKeycloakAdmin:
    deleted: list = []

    async def delete_user(self, user_id):
        _FakeKeycloakAdmin.deleted.append(user_id)


@pytest.fixture
def env(monkeypatch):
    """Committed-data world: settings control, factories, cleanup, fakes."""
    try:
        engine = create_engine(_database_url())
        engine.connect().close()
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"Postgres not reachable: {exc}")
    Session = sessionmaker(bind=engine)
    suffix = uuid.uuid4().hex[:10]

    registry = _FakeRegistry()
    redis = _FakeRedis()

    async def _redis():
        return redis

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(auth_mod, "get_plugin_registry", lambda: registry)
    monkeypatch.setattr(auth_mod, "get_redis_client", _redis)
    monkeypatch.setattr(auth_mod, "enforce_login_cap", _noop)
    monkeypatch.setattr(auth_mod, "touch_login_seat", _noop)
    monkeypatch.setattr(auth_mod, "_provision_git_server_account", _noop)
    monkeypatch.setattr(auth_mod, "KeycloakAdminClient", _FakeKeycloakAdmin)
    _FakeKeycloakAdmin.deleted = []

    setup = Session()
    saved = setup.query(InstanceSettings).first()
    saved_state = None
    if saved is not None:
        saved_state = {
            c: getattr(saved, c)
            for c in (
                "max_workspace_users",
                "max_concurrent_logins",
                "login_idle_minutes",
                "registration_mode",
                "max_registered_users",
                "referral_invites_per_user",
                "pilot_course_ids",
            )
        }
    setup.close()

    def settings(**values):
        s = Session()
        row = s.query(InstanceSettings).first()
        if row is None:
            row = InstanceSettings(singleton=1)
            s.add(row)
        row.registration_mode = values.get("registration_mode", "open")
        row.max_registered_users = values.get("max_registered_users")
        row.referral_invites_per_user = values.get("referral_invites_per_user", 2)
        row.pilot_course_ids = values.get("pilot_course_ids", [])
        s.commit()
        s.close()

    def no_settings():
        s = Session()
        s.query(InstanceSettings).delete()
        s.commit()
        s.close()

    def make_user(name, *, role=None):
        s = Session()
        u = User(given_name=name, family_name="Test", email=f"{name}.{suffix}@test.local")
        s.add(u)
        s.flush()
        if role:
            s.add(UserRole(user_id=u.id, role_id=role))
        s.commit()
        uid = str(u.id)
        s.close()
        return uid

    def make_invite(*, created_by=None, max_uses=1, expired=False, email=None):
        s = Session()
        delta = timedelta(days=-1 if expired else 7)
        inv = InviteLink(
            token=f"tok-{uuid.uuid4().hex}",
            created_by=created_by,
            max_uses=max_uses,
            use_count=0,
            email=email,
            expires_at=datetime.now(timezone.utc) + delta,
            roles=[],
            note=f"test-{suffix}",
        )
        s.add(inv)
        s.commit()
        token = inv.token
        s.close()
        return token

    def identity(name, *, verified=True, groups=()):
        code = f"code-{name}-{uuid.uuid4().hex[:6]}"
        registry.identities[code] = UserInfo(
            provider_id=f"kc-{name}-{suffix}",
            email=f"{name}.{suffix}@test.local",
            given_name=name,
            family_name="Test",
            groups=list(groups),
            attributes={"email_verified": verified},
        )
        return code

    def login(name, *, invite=None, verified=True, groups=()):
        """Run the real first-login path; returns the result or the refusal."""
        code = identity(name, verified=verified, groups=groups)
        s = Session()
        try:
            return asyncio.run(
                handle_sso_callback(
                    provider="keycloak",
                    code=code,
                    state="state",
                    state_data={"invite_code": invite},
                    callback_url="http://test/callback",
                    db=s,
                )
            )
        except RegistrationRefused as refusal:
            return refusal
        finally:
            s.close()

    def user_row(name):
        s = Session()
        u = s.query(User).filter(User.email == f"{name}.{suffix}@test.local").first()
        out = None
        if u is not None:
            out = SimpleNamespace(
                id=str(u.id),
                referred_by=u.referred_by_user_id and str(u.referred_by_user_id),
                via_invite=u.registered_via_invite_id and str(u.registered_via_invite_id),
            )
        s.close()
        return out

    def invite(token):
        s = Session()
        inv = s.query(InviteLink).filter(InviteLink.token == token).first()
        out = SimpleNamespace(id=str(inv.id), use_count=inv.use_count, status=invite_public_status(inv))
        s.close()
        return out

    def registered():
        s = Session()
        n = count_registered_users(s)
        s.close()
        return n

    world = SimpleNamespace(
        Session=Session, suffix=suffix, settings=settings, no_settings=no_settings,
        make_user=make_user, make_invite=make_invite, login=login, user=user_row,
        invite=invite, registered=registered, identity=identity,
        kc_deleted=_FakeKeycloakAdmin.deleted,
    )
    try:
        yield world
    finally:
        s = Session()
        pattern = f"%.{suffix}@test.local"
        ids = [u.id for u in s.query(User.id).filter(User.email.like(pattern))]
        s.query(InviteLink).filter(
            (InviteLink.note == f"test-{suffix}") | (InviteLink.created_by.in_(ids))
        ).delete(synchronize_session=False)
        s.query(User).filter(User.id.in_(ids)).delete(synchronize_session=False)
        s.query(InstanceSettings).delete()
        if saved_state is not None:
            s.add(InstanceSettings(singleton=1, **saved_state))
        s.commit()
        s.close()
        engine.dispose()


# ---------------------------------------------------------------------------
# Sequential behaviour
# ---------------------------------------------------------------------------


def test_invite_only_without_a_code_creates_no_user_and_keeps_the_keycloak_account(env):
    env.settings(registration_mode="invite_only")
    result = env.login("nocode")
    assert isinstance(result, RegistrationRefused)
    assert result.reason == "invite_required"
    assert env.user("nocode") is None
    # Refusal only logs out; no Keycloak account is ever deleted.
    assert env.kc_deleted == []
    assert result.id_token.startswith("idtoken-")


def test_valid_code_creates_the_user_consumes_the_invite_and_records_the_referrer(env):
    env.settings(registration_mode="invite_only")
    referrer = env.make_user("referrer")
    token = env.make_invite(created_by=referrer)
    result = env.login("newbie", invite=token)
    assert not isinstance(result, RegistrationRefused), result
    assert result["is_new_user"] is True
    row = env.user("newbie")
    assert row is not None and row.id == result["user_id"]
    inv = env.invite(token)
    assert inv.use_count == 1 and inv.status == "used"
    assert row.referred_by == referrer
    assert row.via_invite == inv.id
    assert env.kc_deleted == []


def test_the_same_code_cannot_admit_a_second_person(env):
    env.settings(registration_mode="invite_only")
    token = env.make_invite()
    assert not isinstance(env.login("first", invite=token), RegistrationRefused)
    second = env.login("second", invite=token)
    assert isinstance(second, RegistrationRefused)
    assert second.reason == "invite_invalid"
    assert env.user("second") is None
    assert env.invite(token).use_count == 1


def test_expired_code_is_refused(env):
    env.settings(registration_mode="invite_only")
    token = env.make_invite(expired=True)
    result = env.login("late", invite=token)
    assert isinstance(result, RegistrationRefused) and result.reason == "invite_invalid"
    assert env.user("late") is None


def test_cap_reached_refuses_even_a_valid_code_and_leaves_it_unspent(env):
    env.settings(registration_mode="invite_only", max_registered_users=env.registered())
    token = env.make_invite()
    result = env.login("capped", invite=token)
    assert isinstance(result, RegistrationRefused) and result.reason == "full"
    assert env.user("capped") is None
    assert env.invite(token).use_count == 0
    assert env.kc_deleted == []


def test_cap_applies_in_open_mode_too(env):
    env.settings(registration_mode="open", max_registered_users=env.registered())
    result = env.login("openfull")
    assert isinstance(result, RegistrationRefused) and result.reason == "full"
    assert env.user("openfull") is None


def test_closed_mode_refuses_even_with_a_valid_code(env):
    env.settings(registration_mode="closed")
    token = env.make_invite()
    result = env.login("closedout", invite=token)
    assert isinstance(result, RegistrationRefused) and result.reason == "closed"
    assert env.user("closedout") is None
    assert env.invite(token).use_count == 0


def test_existing_users_always_sign_in(env):
    env.settings(registration_mode="invite_only")
    token = env.make_invite()
    assert not isinstance(env.login("regular", invite=token), RegistrationRefused)
    env.settings(registration_mode="closed", max_registered_users=0)
    # Same identity again (same provider subject): no invite, closed, full.
    again = env.login("regular")
    assert not isinstance(again, RegistrationRefused), again
    assert again["is_new_user"] is False


def test_staff_do_not_count_against_the_cap(env):
    before = env.registered()
    env.make_user("staffer", role="_admin")
    assert env.registered() == before
    env.settings(registration_mode="invite_only", max_registered_users=before + 1)
    token = env.make_invite()
    assert not isinstance(env.login("afterstaff", invite=token), RegistrationRefused)


def test_keycloak_administrators_are_admitted_without_code_when_full(env):
    env.settings(registration_mode="invite_only", max_registered_users=0)
    result = env.login("kcadmin", groups=["/administrators"])
    assert not isinstance(result, RegistrationRefused), result
    assert env.user("kcadmin") is not None


def test_open_mode_is_unchanged_without_settings(env):
    env.no_settings()
    result = env.login("oldstyle", verified=True)
    assert not isinstance(result, RegistrationRefused), result
    assert env.user("oldstyle") is not None
    env.settings(registration_mode="open")
    assert not isinstance(env.login("oldstyle2", verified=True), RegistrationRefused)


def test_open_mode_still_refuses_an_unverified_email(env):
    """An unverified address must never become a user's email (PR #242)."""
    env.settings(registration_mode="open")
    result = env.login("openunverified", verified=False)
    assert isinstance(result, RegistrationRefused) and result.reason == "email_unverified"
    assert env.user("openunverified") is None
    assert env.kc_deleted == []


# ---------------------------------------------------------------------------
# Email + password registration (Keycloak registration form)
# ---------------------------------------------------------------------------


def test_unverified_email_is_refused_but_keeps_the_keycloak_account_and_invite(env):
    env.settings(registration_mode="invite_only")
    token = env.make_invite()
    result = env.login("unverified", invite=token, verified=False)
    assert isinstance(result, RegistrationRefused) and result.reason == "email_unverified"
    assert env.user("unverified") is None
    assert env.invite(token).use_count == 0
    # Not an orphan: the person only has to click the verification link.
    assert env.kc_deleted == []


def test_verified_email_registration_with_a_valid_code_is_admitted(env):
    env.settings(registration_mode="invite_only")
    token = env.make_invite()
    result = env.login("emailreg", invite=token, verified=True)
    assert not isinstance(result, RegistrationRefused), result
    assert env.user("emailreg") is not None


def test_refused_registration_redirect_logs_out_of_keycloak(monkeypatch):
    from computor_backend.api import auth as api_auth

    plugin = SimpleNamespace(_oidc_config={"end_session_endpoint": "https://kc/logout"})
    monkeypatch.setattr(
        api_auth, "get_plugin_registry",
        lambda: SimpleNamespace(get_plugin=lambda name: plugin),
    )
    monkeypatch.setenv("NEXT_PUBLIC_API_URL", "https://computor.example/api")

    for reason in ("full", "email_unverified"):
        refusal = RegistrationRefused(reason)
        refusal.id_token = "tok"
        loc = api_auth._registration_refused_redirect("keycloak", refusal).headers["location"]
        assert loc.startswith("https://kc/logout?")
        assert f"state={reason}" in loc and "id_token_hint=tok" in loc
        assert "post_logout_redirect_uri=https%3A%2F%2Fcomputor.example%2Fjoin%2Frefused" in loc


# ---------------------------------------------------------------------------
# Concurrency: two connections racing
# ---------------------------------------------------------------------------


def _race(env, monkeypatch, first, second):
    """Run two first logins; ``first`` is held after admission, before commit.

    The hold sits in ``record_invite`` — after ``admit_new_user`` has taken the
    settings-row lock (and spent the invite) but before the user row commits.
    Without the lock, ``second`` would count the same users, see the same
    unspent seat, and be admitted too.
    """
    held = threading.Event()
    release = threading.Event()
    real_record = auth_mod.record_invite

    def _record(user, consumed):
        real_record(user, consumed)
        if user.email.startswith(f"{first[0]}."):
            held.set()
            release.wait(timeout=30)

    monkeypatch.setattr(auth_mod, "record_invite", _record)
    results = {}

    def _run(name, invite):
        results[name] = env.login(name, invite=invite)

    a = threading.Thread(target=_run, args=first)
    b = threading.Thread(target=_run, args=second)
    try:
        a.start()
        assert held.wait(timeout=10), "first login never reached the hold point"
        b.start()
        b.join(timeout=2)
        assert b.is_alive(), "second login must wait on the lock while the first is open"
    finally:
        release.set()
        a.join(timeout=10)
        b.join(timeout=10)
    return results


def test_racing_for_the_last_seat_admits_exactly_one(env, monkeypatch):
    env.settings(registration_mode="invite_only", max_registered_users=env.registered() + 1)
    t1, t2 = env.make_invite(), env.make_invite()
    results = _race(env, monkeypatch, ("racer1", t1), ("racer2", t2))
    assert not isinstance(results["racer1"], RegistrationRefused), results["racer1"]
    assert isinstance(results["racer2"], RegistrationRefused)
    assert results["racer2"].reason == "full"
    assert env.user("racer1") is not None and env.user("racer2") is None
    assert env.invite(t2).use_count == 0


def test_racing_with_the_same_code_admits_exactly_one(env, monkeypatch):
    env.settings(registration_mode="invite_only")
    token = env.make_invite()
    results = _race(env, monkeypatch, ("twin1", token), ("twin2", token))
    assert not isinstance(results["twin1"], RegistrationRefused), results["twin1"]
    assert isinstance(results["twin2"], RegistrationRefused)
    assert results["twin2"].reason == "invite_invalid"
    assert env.user("twin2") is None
    assert env.invite(token).use_count == 1


# ---------------------------------------------------------------------------
# Referral invites, pilot courses, password-invite path
# ---------------------------------------------------------------------------


def test_referral_invites_are_created_once_and_admit_a_friend(env):
    env.settings(registration_mode="invite_only", referral_invites_per_user=2)
    inviter = env.make_user("inviter")
    s = env.Session()
    first = [i.token for i in ensure_referral_invites(s, inviter)]
    s.close()
    s = env.Session()
    again = [i.token for i in ensure_referral_invites(s, inviter)]
    s.close()
    assert len(first) == 2 and first == again

    assert not isinstance(env.login("friend", invite=first[0]), RegistrationRefused)
    assert env.user("friend").referred_by == inviter
    assert env.invite(first[0]).status == "used"
    assert env.invite(first[1]).status == "valid"


def test_no_referral_invites_are_minted_while_registration_is_open(env):
    env.settings(registration_mode="open")
    inviter = env.make_user("openinviter")
    s = env.Session()
    assert ensure_referral_invites(s, inviter) == []
    s.close()


def test_new_users_are_enrolled_in_pilot_courses(env, monkeypatch):
    from sqlalchemy_utils import Ltree

    import computor_backend.business_logic.course_member_post_create as hook_mod
    from computor_backend.model.course import Course, CourseFamily, CourseGroup, CourseMember
    from computor_backend.model.organization import Organization

    async def _hook(member, db, permissions=None):
        return None

    monkeypatch.setattr(hook_mod, "course_member_post_create", _hook)

    s = env.Session()
    org = Organization(title="Pilot Org", organization_type="organization",
                       path=Ltree(f"pilot_{env.suffix}"), properties={})
    s.add(org)
    s.flush()
    family = CourseFamily(title="Pilot Family", path=Ltree(f"pilot_{env.suffix}.family"),
                          organization_id=org.id)
    s.add(family)
    s.flush()
    course = Course(title="Pilot Course", path=Ltree(f"pilot_{env.suffix}.family.course"),
                    course_family_id=family.id, organization_id=org.id, public=True,
                    max_self_registrations=1)
    s.add(course)
    s.commit()
    course_id, ids = str(course.id), (org.id, family.id)
    s.close()
    try:
        env.settings(registration_mode="invite_only", pilot_course_ids=[course_id])
        assert not isinstance(env.login("pilot1", invite=env.make_invite()), RegistrationRefused)
        # Course seat cap binds: the second pilot user signs in but is not enrolled.
        assert not isinstance(env.login("pilot2", invite=env.make_invite()), RegistrationRefused)
        s = env.Session()
        members = {str(m.user_id) for m in s.query(CourseMember).filter(
            CourseMember.course_id == course_id)}
        s.close()
        assert members == {env.user("pilot1").id}
    finally:
        s = env.Session()
        s.query(CourseMember).filter(CourseMember.course_id == course_id).delete()
        s.query(CourseGroup).filter(CourseGroup.course_id == course_id).delete()
        s.query(Course).filter(Course.id == course_id).delete()
        s.query(CourseFamily).filter(CourseFamily.id == ids[1]).delete()
        s.query(Organization).filter(Organization.id == ids[0]).delete()
        s.commit()
        s.close()


def test_password_invite_accept_respects_the_cap(env, monkeypatch):
    from computor_backend.api.invites import accept_invite
    from computor_types.invites import InviteAccept

    async def _provision(**kwargs):
        return "kc-id", True

    monkeypatch.setattr(auth_mod, "provision_keycloak_login", _provision)
    env.settings(registration_mode="invite_only", max_registered_users=env.registered())
    token = env.make_invite(email=f"pwuser.{env.suffix}@test.local")
    payload = InviteAccept(given_name="Pw", family_name="User",
                           email=f"pwuser.{env.suffix}@test.local", password="x")
    s = env.Session()
    with pytest.raises(RegistrationRefused):
        asyncio.run(accept_invite(token, payload, s))
    s.rollback()
    s.close()
    assert env.user("pwuser") is None
    assert env.invite(token).use_count == 0

    env.settings(registration_mode="invite_only", max_registered_users=env.registered() + 1)
    s = env.Session()
    asyncio.run(accept_invite(token, payload, s))
    s.close()
    assert env.user("pwuser").via_invite == env.invite(token).id


def test_referral_invites_cannot_be_redeemed_through_the_password_path(env, monkeypatch):
    """That path marks the email verified, which /join must not let a friend skip."""
    from computor_backend.api.invites import accept_invite
    from computor_backend.exceptions import BadRequestException
    from computor_types.invites import InviteAccept

    async def _provision(**kwargs):  # pragma: no cover - must not be reached
        raise AssertionError("Keycloak login provisioned for a referral invite")

    monkeypatch.setattr(auth_mod, "provision_keycloak_login", _provision)
    env.settings(registration_mode="invite_only")
    inviter = env.make_user("pwinviter")
    s = env.Session()
    token = ensure_referral_invites(s, inviter)[0].token
    s.close()
    payload = InviteAccept(given_name="Pw", family_name="Friend",
                           email=f"pwfriend.{env.suffix}@test.local", password="x")
    s = env.Session()
    with pytest.raises(BadRequestException):
        asyncio.run(accept_invite(token, payload, s))
    s.close()
    assert env.user("pwfriend") is None
    assert env.invite(token).use_count == 0


def test_same_identity_racing_its_own_first_login_is_one_user_and_never_refused(env, monkeypatch):
    """Reviewer repro: two callbacks of ONE identity for the last seat.

    Without per-identity serialisation both miss the account lookup; one takes
    the seat and the other is refused as "full" for a login that succeeded.
    With it, the second waits, then finds the account and simply signs in.
    """
    env.settings(registration_mode="invite_only", max_registered_users=env.registered() + 1)
    token = env.make_invite()
    held, release = threading.Event(), threading.Event()
    real_record = auth_mod.record_invite

    def _record(user, consumed):
        real_record(user, consumed)
        held.set()
        release.wait(timeout=30)

    monkeypatch.setattr(auth_mod, "record_invite", _record)
    results = []

    def _run():
        results.append(env.login("samebody", invite=token))

    a, b = threading.Thread(target=_run), threading.Thread(target=_run)
    try:
        a.start()
        assert held.wait(timeout=10)
        b.start()
        b.join(timeout=2)
        assert b.is_alive(), "the second callback must wait for the first"
    finally:
        release.set()
        a.join(timeout=10)
        b.join(timeout=10)
    assert len(results) == 2
    assert not any(isinstance(r, RegistrationRefused) for r in results), results
    assert sorted(r["is_new_user"] for r in results) == [False, True]
    assert results[0]["user_id"] == results[1]["user_id"]
    assert env.kc_deleted == []


def test_generic_invite_in_gated_mode_must_use_join(env, monkeypatch):
    """The password path trusts the typed email; while gated it needs a bound invite."""
    from computor_backend.api.invites import accept_invite
    from computor_backend.exceptions import BadRequestException
    from computor_types.invites import InviteAccept

    async def _provision(**kwargs):  # pragma: no cover - must not be reached
        raise AssertionError("provisioned")

    monkeypatch.setattr(auth_mod, "provision_keycloak_login", _provision)
    env.settings(registration_mode="invite_only")
    token = env.make_invite()
    s = env.Session()
    with pytest.raises(BadRequestException):
        asyncio.run(accept_invite(token, InviteAccept(
            given_name="G", family_name="U", email=f"generic.{env.suffix}@test.local",
            password="x"), s))
    s.close()
    assert env.invite(token).use_count == 0


def test_two_password_accepts_of_a_single_use_invite_admit_exactly_one(env, monkeypatch):
    """Reviewer repro: both accepted and use_count stayed 1.

    The first accept is held inside Keycloak provisioning — after the invite
    is spent, before commit. The second must wait on the invite row and then
    be refused; exactly one user may exist afterwards.
    """
    from computor_backend.api.invites import accept_invite
    from computor_backend.exceptions import BadRequestException
    from computor_types.invites import InviteAccept

    held, release = threading.Event(), threading.Event()

    async def _provision(**kwargs):
        if kwargs["email"].startswith("pwrace1."):
            held.set()
            await asyncio.get_running_loop().run_in_executor(None, release.wait, 30)
        return "kc", True

    monkeypatch.setattr(auth_mod, "provision_keycloak_login", _provision)
    env.settings(registration_mode="open")
    token = env.make_invite()
    results = {}

    def _run(name):
        s = env.Session()
        try:
            results[name] = asyncio.run(accept_invite(token, InviteAccept(
                given_name=name, family_name="Race", email=f"{name}.{env.suffix}@test.local",
                password="x"), s))
        except Exception as exc:  # noqa: BLE001 - the outcome is the assertion
            results[name] = exc
        finally:
            s.close()

    a = threading.Thread(target=_run, args=("pwrace1",))
    b = threading.Thread(target=_run, args=("pwrace2",))
    try:
        a.start()
        assert held.wait(timeout=10), "first accept never reached provisioning"
        b.start()
        b.join(timeout=2)
        assert b.is_alive(), "second accept must wait on the spent invite row"
    finally:
        release.set()
        a.join(timeout=10)
        b.join(timeout=10)
    assert isinstance(results["pwrace1"], dict), results["pwrace1"]
    assert isinstance(results["pwrace2"], BadRequestException), results["pwrace2"]
    assert env.user("pwrace1") is not None and env.user("pwrace2") is None
    assert env.invite(token).use_count == 1
