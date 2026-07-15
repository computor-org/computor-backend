"""Tests for the GDPR consent gate.

Covers: middleware gating (whitelisted vs. not, consented vs. not),
identity resolution (bearer / cookie / sso_session fallback / API-token /
service principals, credential precedence), policy-version bump re-gating,
withdrawal, Redis cache invalidation, whitelist boundary collisions
(/docs vs /documents, /ws vs /workspaces), downstream exception passthrough,
language fallback, and service-level version checks.

The DB fallbacks are patched (the sqlite test_db fixture cannot create the
postgres-typed tables); Redis is replaced by an in-memory fake.
"""

import asyncio
import hashlib
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from computor_backend.business_logic import consent as consent_logic
from computor_backend.business_logic.consent import ConsentService
from computor_backend.exceptions import BadRequestException, NotFoundException
from computor_backend.middleware import principal_lookup
from computor_backend.middleware.consent import ConsentGateMiddleware
from computor_backend.utils.token_hash import hash_token

CURRENT = "2026-07-01"
NEXT = "2026-08-01"
TOKEN = "test-access-token"
API_TOKEN = "ctp_" + "a" * 32
USER = "11111111-1111-1111-1111-111111111111"
OTHER_USER = "22222222-2222-2222-2222-222222222222"


class FakeRedis:
    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ex=None):
        self.store[key] = value

    async def delete(self, *keys):
        for key in keys:
            self.store.pop(key, None)


@pytest.fixture
def fake_redis(monkeypatch):
    redis = FakeRedis()

    async def _get_redis_client():
        return redis

    monkeypatch.setattr("computor_backend.redis_cache.get_redis_client", _get_redis_client)
    return redis


@pytest.fixture
def gate_state(monkeypatch):
    """Controls what the DB fallbacks see."""
    state = {"version": CURRENT, "consents": set(), "api_tokens": {}}  # consents: {(user_id, version)}
    monkeypatch.setattr(
        consent_logic, "_load_current_version_from_db",
        lambda: state["version"],
    )
    monkeypatch.setattr(
        ConsentGateMiddleware, "_db_has_consent",
        staticmethod(lambda user_id, version: (user_id, version) in state["consents"]),
    )
    monkeypatch.setattr(
        principal_lookup, "_resolve_api_token_from_db",
        lambda token: state["api_tokens"].get(token),
    )
    return state


@pytest.fixture
def app(fake_redis, gate_state):
    app = FastAPI()
    app.add_middleware(ConsentGateMiddleware, enabled=True)
    app.state.protected_calls = 0

    @app.get("/protected")
    def protected():
        app.state.protected_calls += 1
        return {"ok": True}

    @app.get("/boom")
    def boom():
        app.state.protected_calls += 1
        raise ValueError("endpoint blew up")

    @app.post("/user-roles")
    def user_roles():
        return {"ok": True}

    @app.get("/documents/some-doc")
    def documents():
        return {"gated": True}

    @app.get("/workspaces/roles")
    def workspace_roles():
        return {"gated": True}

    @app.get("/consent/status")
    def consent_status():
        return {"whitelisted": True}

    @app.get("/auth/providers")
    def auth_providers():
        return {"whitelisted": True}

    @app.get("/user")
    def user_me():
        return {"whitelisted": True}

    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def seed_principal(redis, token, user_id, is_service=False, prefix="sso_permissions"):
    key = hashlib.sha256(f"{prefix}:{token}".encode()).hexdigest()
    redis.store[key] = json.dumps({"user_id": user_id, "is_service": is_service})


def bearer(token=TOKEN):
    return {"Authorization": f"Bearer {token}"}


def run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Middleware gating
# ---------------------------------------------------------------------------

class TestConsentGateMiddleware:
    def test_unauthenticated_request_passes_through(self, client):
        # No credentials -> gate defers to the route's auth dependency.
        assert client.get("/protected").status_code == 200

    def test_unconsented_user_blocked_with_stable_body(self, client, fake_redis):
        seed_principal(fake_redis, TOKEN, USER)
        response = client.get("/protected", headers=bearer())
        assert response.status_code == 403
        body = response.json()
        # Stable machine-readable fields are pinned; the human `message` just has
        # to reference the required version.
        assert body["error"] == "consent_required"
        assert body["required_version"] == CURRENT
        assert body["error_code"] == "AUTHZ_006"
        assert CURRENT in body["message"]

    def test_consented_user_passes(self, client, fake_redis, gate_state):
        seed_principal(fake_redis, TOKEN, USER)
        gate_state["consents"].add((USER, CURRENT))
        assert client.get("/protected", headers=bearer()).status_code == 200

    def test_whitelisted_paths_pass_without_consent(self, client, fake_redis):
        seed_principal(fake_redis, TOKEN, USER)
        for path in ("/consent/status", "/auth/providers", "/user"):
            assert client.get(path, headers=bearer()).status_code == 200, path

    def test_get_only_exemption_does_not_cover_mutations_elsewhere(self, client, fake_redis):
        seed_principal(fake_redis, TOKEN, USER)
        # /user is exempt for GET, but /user-roles must stay gated.
        assert client.post("/user-roles", headers=bearer()).status_code == 403

    def test_docs_exemption_does_not_cover_documents_api(self, client, fake_redis):
        seed_principal(fake_redis, TOKEN, USER)
        assert client.get("/documents/some-doc", headers=bearer()).status_code == 403

    def test_workspaces_not_exempted_by_ws(self, client, fake_redis):
        seed_principal(fake_redis, TOKEN, USER)
        assert client.get("/workspaces/roles", headers=bearer()).status_code == 403

    def test_downstream_exception_propagates_and_runs_once(self, app, fake_redis, gate_state):
        # The fail-open handler must not swallow endpoint errors or re-invoke
        # the app (duplicate side effects).
        seed_principal(fake_redis, TOKEN, USER)
        gate_state["consents"].add((USER, CURRENT))
        client = TestClient(app, raise_server_exceptions=True)
        with pytest.raises(ValueError, match="endpoint blew up"):
            client.get("/boom", headers=bearer())
        assert app.state.protected_calls == 1

    def test_options_preflight_passes(self, client, fake_redis):
        seed_principal(fake_redis, TOKEN, USER)
        response = client.options("/protected", headers=bearer())
        assert response.status_code != 403

    def test_cookie_token_resolution(self, client, fake_redis):
        seed_principal(fake_redis, TOKEN, USER)
        response = client.get("/protected", cookies={"ct_access_token": TOKEN})
        assert response.status_code == 403
        assert response.json()["error"] == "consent_required"

    def test_sso_session_fallback_when_principal_cache_expired(self, client, fake_redis):
        # No principal cache entry, but a live sso_session -> still resolved and gated.
        fake_redis.store[f"sso_session:{hash_token(TOKEN)}"] = json.dumps({"user_id": USER})
        assert client.get("/protected", headers=bearer()).status_code == 403

    def test_api_token_db_fallback_gates_uncached_tokens(self, client, gate_state):
        # No principal cache entry -> DB fallback resolves the token's user.
        gate_state["api_tokens"][API_TOKEN] = {"user_id": USER, "is_admin": False, "is_service": False}
        response = client.get("/protected", headers={"X-API-Token": API_TOKEN})
        assert response.status_code == 403

    def test_api_token_precedence_over_bearer(self, client, fake_redis, gate_state):
        # Matches parse_authorization_header: X-API-Token wins over Authorization,
        # so the gate judges the same identity the route will authenticate.
        seed_principal(fake_redis, TOKEN, USER)  # unconsented SSO user
        gate_state["api_tokens"][API_TOKEN] = {"user_id": OTHER_USER, "is_admin": False, "is_service": True}
        response = client.get(
            "/protected", headers={**bearer(), "X-API-Token": API_TOKEN}
        )
        assert response.status_code == 200  # service principal exempt

    def test_service_principal_passes(self, client, fake_redis):
        seed_principal(fake_redis, TOKEN, USER, is_service=True)
        assert client.get("/protected", headers=bearer()).status_code == 200

    def test_gate_inactive_without_policy_version(self, client, fake_redis, gate_state):
        seed_principal(fake_redis, TOKEN, USER)
        gate_state["version"] = None
        assert client.get("/protected", headers=bearer()).status_code == 200

    def test_gate_disabled_via_flag(self, fake_redis, gate_state):
        app = FastAPI()
        app.add_middleware(ConsentGateMiddleware, enabled=False)

        @app.get("/protected")
        def protected():
            return {"ok": True}

        seed_principal(fake_redis, TOKEN, USER)
        assert TestClient(app).get("/protected", headers=bearer()).status_code == 200


# ---------------------------------------------------------------------------
# Caching, version bump, withdrawal
# ---------------------------------------------------------------------------

class TestConsentCacheBehavior:
    def test_gate_result_is_cached(self, client, fake_redis, gate_state):
        seed_principal(fake_redis, TOKEN, USER)
        gate_state["consents"].add((USER, CURRENT))
        assert client.get("/protected", headers=bearer()).status_code == 200
        assert fake_redis.store[consent_logic.consent_cache_key(USER, CURRENT)] == "1"

        # DB flips, but the cached "1" still answers until invalidated.
        gate_state["consents"].clear()
        assert client.get("/protected", headers=bearer()).status_code == 200

    def test_invalidation_regates_after_withdrawal(self, client, fake_redis, gate_state):
        seed_principal(fake_redis, TOKEN, USER)
        gate_state["consents"].add((USER, CURRENT))
        assert client.get("/protected", headers=bearer()).status_code == 200

        # Withdrawal: DB row withdrawn + cache invalidated (what the endpoint does).
        gate_state["consents"].clear()
        run(consent_logic.invalidate_consent_cache(USER, CURRENT))
        assert client.get("/protected", headers=bearer()).status_code == 403

    def test_version_bump_regates_users(self, client, fake_redis, gate_state):
        seed_principal(fake_redis, TOKEN, USER)
        gate_state["consents"].add((USER, CURRENT))
        assert client.get("/protected", headers=bearer()).status_code == 200

        # Publish a new version: DB changes + current-version cache invalidated.
        # The per-user key includes the version, so the stale "1" is never read.
        gate_state["version"] = NEXT
        run(consent_logic.invalidate_current_version_cache())
        response = client.get("/protected", headers=bearer())
        assert response.status_code == 403
        assert response.json()["required_version"] == NEXT

    def test_giving_consent_unblocks_without_relogin(self, client, fake_redis, gate_state):
        seed_principal(fake_redis, TOKEN, USER)
        assert client.get("/protected", headers=bearer()).status_code == 403

        # POST /consent: DB row created + gate cache refreshed (what the endpoint does).
        gate_state["consents"].add((USER, CURRENT))
        run(consent_logic.cache_consent_status(USER, CURRENT, True))
        assert client.get("/protected", headers=bearer()).status_code == 200

    def test_current_version_sentinel_round_trip(self, fake_redis):
        run(consent_logic.cache_current_version(None))
        assert run(consent_logic.get_cached_current_version()) == consent_logic.NO_VERSION_SENTINEL
        run(consent_logic.cache_current_version(CURRENT))
        assert run(consent_logic.get_cached_current_version()) == CURRENT

    def test_resolve_current_version_caches_db_result(self, fake_redis, gate_state):
        assert run(consent_logic.resolve_current_policy_version()) == CURRENT
        # Cached now: a DB change without invalidation is not seen...
        gate_state["version"] = NEXT
        assert run(consent_logic.resolve_current_policy_version()) == CURRENT
        # ...until the cache is invalidated (what publishing does).
        run(consent_logic.invalidate_current_version_cache())
        assert run(consent_logic.resolve_current_policy_version()) == NEXT


# ---------------------------------------------------------------------------
# Service-level logic (repositories mocked)
# ---------------------------------------------------------------------------

def make_service(active_consent=None):
    service = ConsentService(MagicMock())
    service.policy_versions = MagicMock()
    service.consents = MagicMock()
    service.consents.get_active_consent.return_value = active_consent
    return service


class TestConsentService:
    def test_status_unconsented(self):
        service = make_service()
        status = service.get_status(USER, CURRENT)
        assert status == {"required_version": CURRENT, "has_consented": False, "granted_at": None}

    def test_status_consented(self):
        active = SimpleNamespace(granted_at="2026-07-02T10:00:00Z")
        service = make_service(active_consent=active)
        status = service.get_status(USER, CURRENT)
        assert status["has_consented"] is True
        assert status["granted_at"] == active.granted_at

    def test_status_without_configured_policy(self):
        service = make_service()
        status = service.get_status(USER, None)
        assert status == {"required_version": None, "has_consented": True, "granted_at": None}

    def test_record_consent_rejects_stale_version(self):
        service = make_service()
        with pytest.raises(BadRequestException):
            service.record_consent(USER, "2020-01-01", required_version=CURRENT)

    def test_record_consent_rejects_when_no_policy(self):
        service = make_service()
        with pytest.raises(BadRequestException):
            service.record_consent(USER, CURRENT, required_version=None)

    def test_record_consent_passes_proof_fields(self):
        service = make_service()
        service.record_consent(
            USER, CURRENT, required_version=CURRENT,
            ip_address="203.0.113.5", user_agent="pytest", purposes={"x": True},
        )
        service.consents.create_consent.assert_called_once_with(
            user_id=USER,
            policy_version=CURRENT,
            ip_address="203.0.113.5",
            user_agent="pytest",
            purposes={"x": True},
        )

    def test_resolve_language_prefers_requested_then_fallback(self):
        service = make_service()
        policy = SimpleNamespace(version=CURRENT, languages=["de", "en"])
        assert service.resolve_language(policy, "de") == "de"
        assert service.resolve_language(policy, "fr") == "en"
        policy_no_en = SimpleNamespace(version=CURRENT, languages=["de"])
        assert service.resolve_language(policy_no_en, "fr") == "de"
        with pytest.raises(NotFoundException):
            service.resolve_language(SimpleNamespace(version=CURRENT, languages=[]), "de")


class TestIpSanitization:
    def test_valid_and_invalid_ips(self):
        from computor_backend.api.consent import _valid_ip_or_none
        assert _valid_ip_or_none("203.0.113.5") == "203.0.113.5"
        assert _valid_ip_or_none(" 2001:db8::1 ") == "2001:db8::1"
        # Client-controlled Forwarded/XFF garbage must become NULL, not a 500.
        assert _valid_ip_or_none("unknown") is None
        assert _valid_ip_or_none("_gazonk") is None
        assert _valid_ip_or_none("") is None
        assert _valid_ip_or_none(None) is None
