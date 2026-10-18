"""Mandatory TOTP for administrators and managers (computor-org/issues#485).

Unit level, no infrastructure:
* the second-factor evidence check and the enforcement switch;
* the Keycloak plugin carries ``amr`` evidence from a *verified* ID token into
  the auth result, and the SSO session records it;
* only SSO sessions are gated; API tokens are not;
* the 403 handler explains withheld roles with AUTHZ_007;
* the Keycloak membership sync grants, enrols, revokes and prunes correctly
  (against an in-memory fake of the admin endpoints it uses);
* user_role commits, and only those, schedule the sync.

The Principal gate itself is exercised against a real database in
test_admin_mfa_db.py, and the Keycloak side against a real Keycloak in
ops/keycloak/test_mfa_live.py.
"""

import json
import time
from types import SimpleNamespace
from unittest.mock import patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from computor_backend.auth import mfa
from computor_backend.auth.keycloak import KeycloakAuthPlugin
from computor_backend.business_logic import admin_mfa
from computor_backend.exceptions import ForbiddenException
from computor_backend.exceptions.error_handlers import computor_exception_handler
from computor_backend.permissions.auth import AuthenticationResult


@pytest.fixture
def enforced(monkeypatch):
    monkeypatch.setenv("KEYCLOAK_ENABLED", "true")
    monkeypatch.setenv("KEYCLOAK_ADMIN_MFA", "true")


# ---------------------------------------------------------------------------
# Evidence and switch
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("claims, expected", [
    ({"amr": ["otp"]}, True),
    ({"amr": ["pwd", "otp"]}, True),
    ({"amr": "otp"}, True),
    ({"amr": ["hwk"]}, True),
    ({"amr": []}, False),            # what Keycloak emits without references
    ({"amr": ["pwd"]}, False),
    ({"acr": "1"}, False),           # acr alone says nothing about factors
    ({"amr": [None, 5]}, False),
    ({}, False),
    (None, False),
])
def test_has_mfa_evidence(claims, expected):
    assert mfa.has_mfa_evidence(claims) is expected


@pytest.mark.parametrize("enabled, flag, expected", [
    ("true", "true", True),
    ("true", None, False),           # code default is off; the prod overlay sets true
    ("true", "false", False),
    ("false", "true", False),        # no Keycloak, nothing to gate on
])
def test_enforcement_switch(monkeypatch, enabled, flag, expected):
    monkeypatch.setenv("KEYCLOAK_ENABLED", enabled)
    if flag is None:
        monkeypatch.delenv("KEYCLOAK_ADMIN_MFA", raising=False)
    else:
        monkeypatch.setenv("KEYCLOAK_ADMIN_MFA", flag)
    assert mfa.admin_mfa_enforced() is expected


def test_elevated_roles_fail_closed():
    roles = ["_admin", "_user_manager", "_organization_manager", "_example_manager",
             "_git_manager", "_service_manager", "_workspace_maintainer", "_workspace_user",
             "_custom_operator"]
    assert mfa.elevated_roles(roles) == [r for r in roles if r != "_workspace_user"]


# ---------------------------------------------------------------------------
# Keycloak plugin -> SSO session
# ---------------------------------------------------------------------------

@pytest.fixture
def plugin(monkeypatch):
    monkeypatch.delenv("KEYCLOAK_PUBLIC_URL", raising=False)
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private.public_key()))
    jwk.update(kid="k", alg="RS256", use="sig")
    plugin = KeycloakAuthPlugin()
    plugin.keycloak_config.client_id = "computor-backend"
    plugin.keycloak_config.server_url = "https://identity.example"
    plugin.keycloak_config.realm = "computor"
    plugin._oidc_config = {"issuer": "https://identity.example/realms/computor"}
    plugin._jwks = {"keys": [jwk]}

    def id_token(**extra):
        claims = {"sub": "kc-user", "aud": "computor-backend", "iss": plugin._oidc_config["issuer"],
                  "exp": int(time.time()) + 300, "email": "a@example.org", **extra}
        return jwt.encode(claims, private, algorithm="RS256", headers={"kid": "k"})

    return plugin, id_token


@pytest.mark.asyncio
@pytest.mark.parametrize("amr, expected", [(["otp"], True), ([], False), (None, False)])
async def test_plugin_records_amr_from_verified_id_token(plugin, amr, expected):
    plugin, id_token = plugin
    extra = {} if amr is None else {"amr": amr}
    result = await plugin._build_auth_result_from_tokens({"id_token": id_token(**extra)})
    assert result.session_data["mfa"] is expected
    assert result.session_data["amr"] == (amr or [])


@pytest.mark.asyncio
async def test_forged_amr_is_not_accepted(plugin):
    """Evidence only counts from a token Keycloak signed."""
    plugin, _ = plugin
    forged = jwt.encode({"sub": "x", "amr": ["otp"], "aud": "computor-backend",
                         "iss": plugin._oidc_config["issuer"], "exp": int(time.time()) + 300},
                        rsa.generate_private_key(public_exponent=65537, key_size=2048),
                        algorithm="RS256", headers={"kid": "k"})
    with pytest.raises(jwt.InvalidTokenError):
        await plugin._build_auth_result_from_tokens({"id_token": forged})


def test_sso_session_result_is_gated_and_reads_evidence():
    with_mfa = AuthenticationResult.for_sso_session("u", ["_admin"], {"provider": "keycloak", "mfa": True})
    without = AuthenticationResult.for_sso_session("u", ["_admin"], {"provider": "keycloak"})
    truthy_string = AuthenticationResult.for_sso_session("u", ["_admin"], {"mfa": "true"})
    assert (with_mfa.mfa_gated, with_mfa.mfa_verified) == (True, True)
    assert (without.mfa_gated, without.mfa_verified) == (True, False)
    assert truthy_string.mfa_verified is False


def test_api_token_results_are_not_gated():
    result = AuthenticationResult("u", ["_admin"], "api_token")
    assert result.mfa_gated is False


# ---------------------------------------------------------------------------
# 403 explanation
# ---------------------------------------------------------------------------

def _request(withheld):
    state = SimpleNamespace()
    if withheld:
        state.mfa_withheld_roles = withheld
    return SimpleNamespace(state=state, method="GET", url=SimpleNamespace(path="/x"),
                           scope={"type": "http", "path": "/x"}, client=None, headers={})


@pytest.mark.asyncio
async def test_forbidden_with_withheld_roles_explains_mfa():
    response = await computor_exception_handler(_request(["_admin"]), ForbiddenException())
    body = json.loads(response.body)
    assert response.status_code == 403
    assert body["error_code"] == "AUTHZ_007"
    assert "one-time code" in body["message"]


@pytest.mark.asyncio
async def test_forbidden_without_withheld_roles_is_unchanged():
    response = await computor_exception_handler(_request(None), ForbiddenException())
    assert json.loads(response.body)["error_code"] == "AUTHZ_001"


@pytest.mark.asyncio
async def test_consent_refusal_is_not_masked():
    response = await computor_exception_handler(_request(["_admin"]), ForbiddenException(error_code="AUTHZ_006"))
    assert json.loads(response.body)["error_code"] == "AUTHZ_006"


# ---------------------------------------------------------------------------
# Keycloak membership sync
# ---------------------------------------------------------------------------

class FakeResponse:
    def __init__(self, status_code, body=None):
        self.status_code, self._body = status_code, body

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeKeycloak:
    """The admin endpoints apply_keycloak_membership uses, in memory."""

    def __init__(self, users, role_exists=True):
        # users: id -> {"otp": bool, "requiredActions": [...], "role": bool}
        self.users = users
        self.role_exists = role_exists
        self.calls = []

    async def admin_request(self, method, path, json=None, params=None):
        self.calls.append((method, path))
        role = admin_mfa.MFA_REALM_ROLE
        if path == f"/roles/{role}" and method == "GET":
            return FakeResponse(200, {"id": "r", "name": role}) if self.role_exists else FakeResponse(404)
        if path == "/roles" and method == "POST":
            self.role_exists = True
            return FakeResponse(201)
        if path == f"/roles/{role}/users":
            members = [{"id": uid} for uid, u in sorted(self.users.items()) if u.get("role")]
            first, size = params["first"], params["max"]
            return FakeResponse(200, members[first:first + size])
        uid = path.split("/")[2]
        if uid not in self.users:
            return FakeResponse(404)
        user = self.users[uid]
        if path.endswith("/role-mappings/realm"):
            assert json == [{"id": "r", "name": role}]
            user["role"] = method == "POST"
            return FakeResponse(204)
        if path.endswith("/credentials"):
            return FakeResponse(200, [{"type": "password"}] + ([{"type": "otp"}] if user.get("otp") else []))
        if method == "GET":
            return FakeResponse(200, {"id": uid, "username": uid, "requiredActions": list(user.get("requiredActions", []))})
        if method == "PUT":
            assert json["username"] == uid, "full representation must be sent back"
            user["requiredActions"] = json["requiredActions"]
            return FakeResponse(204)
        raise AssertionError((method, path))


def run(coro):
    import asyncio
    return asyncio.run(coro)


def test_sync_grants_and_requests_enrolment_only_without_otp():
    kc = FakeKeycloak({"new": {}, "enrolled": {"otp": True}, "student": {}}, role_exists=False)
    summary = run(admin_mfa.apply_keycloak_membership({"new", "enrolled"}, prune=True, kc=kc))
    assert kc.role_exists
    assert summary["granted"] == ["enrolled", "new"]
    assert summary["enrolment_requested"] == ["new"]
    assert kc.users["new"]["requiredActions"] == ["CONFIGURE_TOTP"]
    assert kc.users["enrolled"].get("requiredActions", []) == []
    assert not kc.users["student"].get("role")


def test_sync_is_idempotent():
    kc = FakeKeycloak({"a": {}, "b": {"otp": True}})
    run(admin_mfa.apply_keycloak_membership({"a", "b"}, prune=True, kc=kc))
    again = run(admin_mfa.apply_keycloak_membership({"a", "b"}, prune=True, kc=kc))
    assert again == {"granted": [], "revoked": [], "enrolment_requested": []}
    assert kc.users["a"]["requiredActions"] == ["CONFIGURE_TOTP"]


def test_prune_revokes_former_holders_only_the_role():
    kc = FakeKeycloak({
        "keeps": {"role": True, "otp": True},
        "former": {"role": True, "requiredActions": ["VERIFY_EMAIL", "CONFIGURE_TOTP"]},
        "former_enrolled": {"role": True, "otp": True, "requiredActions": []},
    })
    summary = run(admin_mfa.apply_keycloak_membership({"keeps"}, prune=True, kc=kc))
    assert summary["revoked"] == ["former", "former_enrolled"]
    assert kc.users["keeps"]["role"] and not kc.users["former"]["role"]
    # Another policy (mail team OTP) may have set CONFIGURE_TOTP: keep it.
    assert kc.users["former"]["requiredActions"] == ["VERIFY_EMAIL", "CONFIGURE_TOTP"]
    assert kc.users["former_enrolled"]["otp"], "an enrolled authenticator is kept"


def test_targeted_sync_only_touches_considered_users():
    kc = FakeKeycloak({"other_admin": {"role": True}, "demoted": {"role": True}})
    summary = run(admin_mfa.apply_keycloak_membership(set(), prune=False, considered={"demoted"}, kc=kc))
    assert summary["revoked"] == ["demoted"]
    assert kc.users["other_admin"]["role"], "a targeted sync must not prune others"


def test_sync_skips_unknown_keycloak_user():
    kc = FakeKeycloak({})
    summary = run(admin_mfa.apply_keycloak_membership({"ghost"}, prune=True, kc=kc))
    assert summary["granted"] == []


def test_role_members_are_paged():
    users = {f"u{i:03d}": {"role": True, "otp": True} for i in range(150)}
    kc = FakeKeycloak(users)
    summary = run(admin_mfa.apply_keycloak_membership(set(users), prune=True, kc=kc))
    assert summary == {"granted": [], "revoked": [], "enrolment_requested": []}


# ---------------------------------------------------------------------------
# Commit hook
# ---------------------------------------------------------------------------

def test_user_role_commit_schedules_sync_other_memberships_do_not():
    from computor_backend.database import (
        _drop_stale_principal_tracking,
        _sync_admin_mfa,
        _track_permission_membership_writes,
    )
    from computor_backend.model.course import CourseMember
    from computor_backend.model.role import UserRole

    session = SimpleNamespace(info={}, new={UserRole(user_id="u1", role_id="_admin"),
                                             CourseMember(user_id="u2", course_id="c")},
                              dirty=set(), deleted=set())
    _track_permission_membership_writes(session, None)
    with patch("computor_backend.business_logic.admin_mfa.schedule_admin_mfa_sync") as schedule:
        _sync_admin_mfa(session)
    schedule.assert_called_once_with({"u1"})

    session = SimpleNamespace(info={}, new={UserRole(user_id="u3", role_id="_admin")}, dirty=set(), deleted=set())
    _track_permission_membership_writes(session, None)
    _drop_stale_principal_tracking(session)  # rollback
    with patch("computor_backend.business_logic.admin_mfa.schedule_admin_mfa_sync") as schedule:
        _sync_admin_mfa(session)
    schedule.assert_not_called()


def test_schedule_is_noop_when_not_enforced(monkeypatch):
    monkeypatch.setenv("KEYCLOAK_ADMIN_MFA", "false")
    with patch("threading.Thread") as thread:
        admin_mfa.schedule_admin_mfa_sync(["u1"])
    thread.assert_not_called()


# ---------------------------------------------------------------------------
# Through FastAPI: dependency injection of the request + the 403 handler
# ---------------------------------------------------------------------------

def test_endpoint_refusal_names_mfa_and_ordinary_endpoint_works(monkeypatch):
    from typing import Annotated

    from fastapi import Depends, FastAPI
    from fastapi.testclient import TestClient

    from computor_backend.exceptions.error_handlers import register_exception_handlers
    from computor_backend.permissions import auth as auth_module
    from computor_backend.permissions.principal import Principal

    async def resolve(credentials):
        return Principal(user_id="u", roles=["_workspace_user"], withheld_roles=["_admin"])

    monkeypatch.setattr(auth_module, "_resolve_principal", resolve)
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/admin-only")
    async def admin_only(principal: Annotated[Principal, Depends(auth_module.get_current_principal)]):
        if not principal.is_admin:
            raise ForbiddenException()
        return {"ok": True}

    @app.get("/ordinary")
    async def ordinary(principal: Annotated[Principal, Depends(auth_module.get_current_principal)]):
        return {"roles": principal.roles}

    client = TestClient(app)
    headers = {"Authorization": "Bearer some-session-token"}
    refused = client.get("/admin-only", headers=headers)
    assert refused.status_code == 403
    assert refused.json()["error_code"] == "AUTHZ_007"
    assert client.get("/ordinary", headers=headers).json() == {"roles": ["_workspace_user"]}
