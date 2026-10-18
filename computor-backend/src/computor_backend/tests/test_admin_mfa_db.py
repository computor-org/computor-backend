"""Admin MFA gate and sync targets against a real Postgres (computor-org/issues#485).

``PrincipalBuilder.build`` must withhold elevated global roles, and the claims
they grant, from an SSO session without second-factor evidence, while keeping
ordinary roles; API tokens, service accounts and sessions with evidence are
untouched. ``keycloak_targets`` must pick exactly the human elevated users.

Rows live in a connection-level transaction that is rolled back. Skips when
Postgres is unreachable (CI: the public-course-contract job's database).
"""

import os
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from computor_backend.business_logic.admin_mfa import keycloak_targets
from computor_backend.model.auth import Account, User
from computor_backend.model.role import Role, RoleClaim, UserRole
from computor_backend.permissions.auth import AuthenticationResult, PrincipalBuilder

MANAGER_CLAIM = ("permissions", "mfa_test_resource:create")
ORDINARY_CLAIM = ("permissions", "mfa_test_workspace:list")


def _database_url() -> str:
    return "postgresql://{}:{}@{}:{}/{}".format(
        os.environ.get("POSTGRES_USER", "postgres"),
        os.environ.get("POSTGRES_PASSWORD", "postgres_secret"),
        os.environ.get("POSTGRES_HOST", "localhost"),
        os.environ.get("POSTGRES_PORT", "5432"),
        os.environ.get("POSTGRES_DB", "computor"),
    )


@pytest.fixture
def db():
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
def people(db):
    suffix = uuid.uuid4().hex[:8]
    # A custom (non-builtin) role stands in for a manager role: any global role
    # other than _workspace_user counts as elevated.
    manager_role, ordinary_role = f"mfa-test-manager-{suffix}", "_workspace_user"
    for role_id in (manager_role, ordinary_role, "_admin"):
        if db.get(Role, role_id) is None:
            db.add(Role(id=role_id, title=role_id, builtin=role_id.startswith("_")))
    db.flush()
    db.add(RoleClaim(role_id=manager_role, claim_type=MANAGER_CLAIM[0], claim_value=MANAGER_CLAIM[1]))
    if db.query(RoleClaim).filter_by(role_id=ordinary_role, claim_value=ORDINARY_CLAIM[1]).first() is None:
        db.add(RoleClaim(role_id=ordinary_role, claim_type=ORDINARY_CLAIM[0], claim_value=ORDINARY_CLAIM[1]))

    def user(name, roles, service=False, keycloak=True):
        u = User(given_name=name, family_name="Mfa", email=f"{name}.{suffix}@test.local", is_service=service)
        db.add(u)
        db.flush()
        for role_id in roles:
            db.add(UserRole(user_id=u.id, role_id=role_id))
        if keycloak:
            db.add(Account(provider="keycloak", type="oidc", provider_account_id=f"kc-{name}-{suffix}",
                           user_id=u.id))
        db.flush()
        return u

    users = {
        "manager": user("manager", [manager_role, ordinary_role]),
        "admin": user("admin", ["_admin"]),
        "student": user("student", [ordinary_role]),
        "service": user("service", [manager_role], service=True),
        "nokeycloak": user("nokeycloak", ["_admin"], keycloak=False),
    }
    return users, manager_role, suffix


def _build(db, user, gated, verified):
    roles = [r.role_id for r in db.query(UserRole).filter(UserRole.user_id == user.id)]
    if gated:
        result = AuthenticationResult.for_sso_session(str(user.id), roles, {"provider": "keycloak", "mfa": verified})
    else:
        result = AuthenticationResult(str(user.id), roles, "api_token")
    return PrincipalBuilder.build(result, db)


@pytest.fixture
def enforced(monkeypatch):
    monkeypatch.setenv("KEYCLOAK_ENABLED", "true")
    monkeypatch.setenv("KEYCLOAK_ADMIN_MFA", "true")


def test_sso_without_evidence_keeps_ordinary_rights_only(db, people, enforced):
    users, manager_role, _ = people
    principal = _build(db, users["manager"], gated=True, verified=False)
    assert principal.roles == ["_workspace_user"]
    assert principal.withheld_roles == [manager_role]
    assert principal.has_general_permission("mfa_test_workspace", "list")
    assert not principal.has_general_permission("mfa_test_resource", "create")

    admin = _build(db, users["admin"], gated=True, verified=False)
    assert admin.is_admin is False and admin.withheld_roles == ["_admin"]
    assert not admin.has_general_permission("anything", "delete")


def test_withheld_roles_survive_the_principal_cache(db, people, enforced):
    users, _, _ = people
    principal = _build(db, users["admin"], gated=True, verified=False)
    cached = type(principal).model_validate_json(principal.model_dump_json())
    assert cached.is_admin is False and cached.withheld_roles == ["_admin"]


@pytest.mark.parametrize("name, gated, verified", [
    ("manager", True, True),       # SSO with OTP evidence
    ("manager", False, False),     # API token (ctp_*, X-API-Token)
    ("service", True, False),      # service account, even on an SSO session
])
def test_ungated_credentials_keep_full_rights(db, people, enforced, name, gated, verified):
    users, manager_role, _ = people
    principal = _build(db, users[name], gated, verified)
    assert manager_role in principal.roles and principal.withheld_roles == []
    assert principal.has_general_permission("mfa_test_resource", "create")


def test_admin_with_evidence_is_admin(db, people, enforced):
    users, _, _ = people
    assert _build(db, users["admin"], gated=True, verified=True).is_admin is True


def test_enforcement_off_changes_nothing(db, people, monkeypatch):
    monkeypatch.setenv("KEYCLOAK_ADMIN_MFA", "false")
    users, manager_role, _ = people
    principal = _build(db, users["manager"], gated=True, verified=False)
    assert manager_role in principal.roles and principal.withheld_roles == []


def test_student_session_is_unaffected(db, people, enforced):
    users, _, _ = people
    principal = _build(db, users["student"], gated=True, verified=False)
    assert principal.roles == ["_workspace_user"] and principal.withheld_roles == []


def test_keycloak_targets(db, people):
    users, _, suffix = people
    ids = [str(u.id) for u in users.values()]
    required, considered = keycloak_targets(db, ids)
    assert required == {f"kc-manager-{suffix}", f"kc-admin-{suffix}"}
    assert considered == {f"kc-{n}-{suffix}" for n in ("manager", "admin", "student", "service")}

    required, considered = keycloak_targets(db, [str(users["student"].id)])
    assert (required, considered) == (set(), {f"kc-student-{suffix}"})

    everyone_required, _ = keycloak_targets(db)
    assert {f"kc-manager-{suffix}", f"kc-admin-{suffix}"} <= everyone_required
    assert f"kc-service-{suffix}" not in everyone_required
    assert f"kc-student-{suffix}" not in everyone_required



# ---------------------------------------------------------------------------
# Review gaps: self-token escalation, refresh after promotion, warm caches
# ---------------------------------------------------------------------------

from computor_backend.tests.test_admin_mfa import FakeRedis, plugin  # noqa: E402,F401 (fixture)


def test_restricted_admin_cannot_trade_session_for_api_token(db, people, enforced):
    """The password-only admin's POST /api-tokens must not yield a ctp_ token."""
    from computor_backend.business_logic.api_tokens import create_api_token
    from computor_backend.exceptions import MfaRequiredException
    from computor_backend.model.service import ApiToken
    from computor_types.api_tokens import ApiTokenCreate

    users, _, _ = people
    restricted = _build(db, users["admin"], gated=True, verified=False)
    with pytest.raises(MfaRequiredException):
        create_api_token(ApiTokenCreate(name="bypass"), restricted, db)
    assert db.query(ApiToken).filter(ApiToken.user_id == users["admin"].id).count() == 0
    # Deliberate: a credential that is not an SSO session keeps the owner's roles.
    assert _build(db, users["admin"], gated=False, verified=False).is_admin is True


def _wire_sso(monkeypatch, db, redis):
    import contextlib

    from computor_backend import redis_cache
    from computor_backend.business_logic import auth as auth_logic
    from computor_backend.business_logic import instance_limits
    from computor_backend.permissions import auth as auth_module

    async def client():
        return redis

    async def touch(*args, **kwargs):
        return None

    monkeypatch.setattr(redis_cache, "get_redis_client", client)
    monkeypatch.setattr(auth_module, "get_redis_client", client)
    monkeypatch.setattr(auth_logic, "get_redis_client", client)
    monkeypatch.setattr(auth_logic, "touch_login_seat", touch)
    monkeypatch.setattr(auth_logic, "login_idle_seconds", lambda db: 3600)
    monkeypatch.setattr(instance_limits, "touch_login_seat", touch)
    monkeypatch.setattr(instance_limits, "login_idle_seconds", lambda db: 3600)
    monkeypatch.setattr(auth_module, "get_db_session", lambda: contextlib.nullcontext(db))


@pytest.mark.asyncio
async def test_password_only_refresh_after_promotion_stays_restricted(db, people, enforced, plugin, monkeypatch):
    """Signed in as an ordinary user without OTP, promoted to _admin, then refreshed."""
    from types import SimpleNamespace

    from computor_backend.business_logic import auth as auth_logic
    from computor_backend.permissions.auth import SSOAuthCredentials, _resolve_principal

    users, _, suffix = people
    kc_plugin, id_token = plugin
    redis = FakeRedis()
    _wire_sso(monkeypatch, db, redis)

    async def refresh(refresh_token):
        # Keycloak re-states the session's amr: a password-only session has none.
        return await kc_plugin._build_auth_result_from_tokens(
            {"id_token": id_token(sub=f"kc-student-{suffix}", amr=[]), "access_token": "at",
             "refresh_token": "rt-2"})

    kc_plugin.refresh_token = refresh

    async def ready(name):
        return kc_plugin

    monkeypatch.setattr(auth_logic, "get_plugin_registry", lambda: SimpleNamespace(
        get_enabled_plugins=lambda: ["keycloak"], ensure_plugin_ready=ready))

    student = users["student"]
    db.add(UserRole(user_id=student.id, role_id="_admin"))  # promotion after sign-in
    db.flush()
    refreshed = await auth_logic.refresh_sso_token("rt-1", "keycloak", None, db)
    principal = await _resolve_principal(SSOAuthCredentials(token=refreshed["access_token"]))
    assert principal.user_id == str(student.id)
    assert principal.is_admin is False and principal.withheld_roles == ["_admin"]


@pytest.mark.asyncio
async def test_enforcement_switch_with_warm_cache_and_failed_invalidation(db, people, monkeypatch):
    """Redis refuses every invalidation write; the policy stamp still re-gates warm entries."""
    import json as _json

    from computor_backend.permissions.auth import SSOAuthCredentials, _resolve_principal
    from computor_backend.utils.token_hash import hash_token

    users, _, _ = people
    redis = FakeRedis()
    _wire_sso(monkeypatch, db, redis)
    redis.data["sso_session:" + hash_token("pw-session")] = _json.dumps(
        {"user_id": str(users["admin"].id), "provider": "keycloak"})
    credentials = SSOAuthCredentials(token="pw-session")
    monkeypatch.setenv("KEYCLOAK_ENABLED", "true")

    monkeypatch.setenv("KEYCLOAK_ADMIN_MFA", "false")
    assert (await _resolve_principal(credentials)).is_admin is True  # cached, pre-enforcement

    redis.fail = True  # no stale stamp, no new cache entry can be written
    monkeypatch.setenv("KEYCLOAK_ADMIN_MFA", "true")
    for _ in range(2):
        principal = await _resolve_principal(credentials)
        assert principal.is_admin is False and principal.withheld_roles == ["_admin"]

    redis.fail = False
    await _resolve_principal(credentials)  # cached under enforcement
    monkeypatch.setenv("KEYCLOAK_ADMIN_MFA", "false")
    assert (await _resolve_principal(credentials)).is_admin is True
