"""Unit tests for KeycloakAuthPlugin.logout() (computor-org/issues#419).

Keycloak ignores a bare ``Authorization: Bearer`` POST to the end-session endpoint,
so the old ``logout()`` reported success while the refresh token kept working. These
tests pin the request shape that actually ends the session and make sure ``logout()``
never reports success that Keycloak did not confirm.

Fully mocked: requests go through an ``httpx.MockTransport``, no live Keycloak.
"""

import logging
from urllib.parse import parse_qs

import httpx
import pytest

from computor_backend.auth import keycloak as keycloak_module
from computor_backend.auth.keycloak import KeycloakAuthPlugin


END_SESSION_ENDPOINT = "https://keycloak.example/realms/computor/protocol/openid-connect/logout"
REVOCATION_ENDPOINT = "https://keycloak.example/realms/computor/protocol/openid-connect/revoke"
REFRESH_TOKEN = "refresh-token-secret-value"
ACCESS_TOKEN = "access-token-secret-value"


def _make_plugin(oidc_config=None):
    plugin = KeycloakAuthPlugin()
    plugin.keycloak_config.client_id = "computor-backend"
    plugin.keycloak_config.client_secret = "client-secret"
    plugin._available = True
    plugin._oidc_config = oidc_config if oidc_config is not None else {
        "end_session_endpoint": END_SESSION_ENDPOINT,
        "revocation_endpoint": REVOCATION_ENDPOINT,
    }
    return plugin


@pytest.fixture
def transport(monkeypatch):
    """Route every httpx.AsyncClient in the plugin through a MockTransport.

    Set ``state["responses"][url]`` to a status code, or to an exception to raise.
    Requests are recorded in ``state["requests"]``.
    """
    state = {"requests": [], "responses": {}}

    def handler(request):
        state["requests"].append(request)
        outcome = state["responses"].get(str(request.url), 404)
        if isinstance(outcome, Exception):
            raise outcome
        return httpx.Response(outcome)

    real_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs.pop("verify", None)
        return real_client(*args, transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(keycloak_module.httpx, "AsyncClient", client_factory)
    return state


def _form(request):
    assert request.method == "POST"
    assert request.headers["content-type"] == "application/x-www-form-urlencoded"
    return {k: v[0] for k, v in parse_qs(request.content.decode()).items()}


@pytest.mark.asyncio
async def test_logout_posts_refresh_token_and_client_credentials_as_form(transport):
    transport["responses"][END_SESSION_ENDPOINT] = 204
    plugin = _make_plugin()

    assert await plugin.logout(ACCESS_TOKEN, REFRESH_TOKEN) is True

    assert len(transport["requests"]) == 1
    request = transport["requests"][0]
    assert str(request.url) == END_SESSION_ENDPOINT
    assert _form(request) == {
        "client_id": "computor-backend",
        "client_secret": "client-secret",
        "refresh_token": REFRESH_TOKEN,
    }
    # The bearer-only request Keycloak ignores is gone.
    assert "authorization" not in request.headers


@pytest.mark.asyncio
async def test_logout_without_refresh_token_returns_false_and_sends_nothing(transport):
    plugin = _make_plugin()

    assert await plugin.logout(ACCESS_TOKEN) is False
    assert await plugin.logout(ACCESS_TOKEN, None) is False
    assert await plugin.logout(ACCESS_TOKEN, "") is False

    assert transport["requests"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [302, 400, 401, 500])
async def test_logout_returns_false_when_every_endpoint_rejects(transport, status):
    transport["responses"][END_SESSION_ENDPOINT] = status
    transport["responses"][REVOCATION_ENDPOINT] = status
    plugin = _make_plugin()

    assert await plugin.logout(ACCESS_TOKEN, REFRESH_TOKEN) is False
    assert [str(r.url) for r in transport["requests"]] == [END_SESSION_ENDPOINT, REVOCATION_ENDPOINT]


@pytest.mark.asyncio
async def test_logout_falls_back_to_revoking_the_refresh_token(transport):
    transport["responses"][END_SESSION_ENDPOINT] = 400
    transport["responses"][REVOCATION_ENDPOINT] = 200
    plugin = _make_plugin()

    assert await plugin.logout(ACCESS_TOKEN, REFRESH_TOKEN) is True

    revoke = transport["requests"][1]
    assert str(revoke.url) == REVOCATION_ENDPOINT
    assert _form(revoke) == {
        "client_id": "computor-backend",
        "client_secret": "client-secret",
        "token": REFRESH_TOKEN,
        "token_type_hint": "refresh_token",
    }


@pytest.mark.asyncio
async def test_logout_falls_back_when_end_session_request_errors(transport):
    transport["responses"][END_SESSION_ENDPOINT] = httpx.ConnectError("boom")
    transport["responses"][REVOCATION_ENDPOINT] = 200
    plugin = _make_plugin()

    assert await plugin.logout(ACCESS_TOKEN, REFRESH_TOKEN) is True


@pytest.mark.asyncio
async def test_logout_returns_false_when_every_request_errors(transport):
    transport["responses"][END_SESSION_ENDPOINT] = httpx.ConnectError("boom")
    transport["responses"][REVOCATION_ENDPOINT] = httpx.ReadTimeout("slow")
    plugin = _make_plugin()

    assert await plugin.logout(ACCESS_TOKEN, REFRESH_TOKEN) is False


@pytest.mark.asyncio
@pytest.mark.parametrize("oidc_config", [None, {}])
async def test_logout_without_usable_oidc_config_returns_false(transport, oidc_config):
    """No endpoint to call means no logout happened, so never report one."""
    plugin = _make_plugin({})
    plugin._oidc_config = oidc_config

    assert await plugin.logout(ACCESS_TOKEN, REFRESH_TOKEN) is False
    assert transport["requests"] == []


@pytest.mark.asyncio
async def test_logout_never_logs_tokens(transport, caplog):
    transport["responses"][END_SESSION_ENDPOINT] = httpx.ConnectError(f"failed for {REFRESH_TOKEN}")
    transport["responses"][REVOCATION_ENDPOINT] = 400
    plugin = _make_plugin()

    with caplog.at_level(logging.DEBUG, logger=keycloak_module.logger.name):
        assert await plugin.logout(ACCESS_TOKEN, REFRESH_TOKEN) is False
        assert await plugin.logout(ACCESS_TOKEN) is False

    assert caplog.records
    assert REFRESH_TOKEN not in caplog.text
    assert ACCESS_TOKEN not in caplog.text


class _FakeRedis:
    def __init__(self, data):
        self.data = dict(data)

    async def get(self, key):
        return self.data.get(key)

    async def delete(self, key):
        self.data.pop(key, None)


class _FakeRegistry:
    def __init__(self, plugin):
        self._plugin = plugin

    def get_enabled_plugins(self):
        return ["keycloak"]

    def get_plugin(self, name):
        return self._plugin if name == "keycloak" else None


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_ended_session", [True, False])
async def test_logout_session_passes_stored_refresh_token_and_always_drops_it(
    monkeypatch, provider_ended_session
):
    """The caller hands Keycloak the stored refresh token and deletes the Redis copy
    whether or not the provider confirmed the logout."""
    import json
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from computor_backend.business_logic import auth as auth_logic

    token_key = "sso_token:keycloak:user-1"
    redis = _FakeRedis({
        token_key: json.dumps({"access_token": ACCESS_TOKEN, "refresh_token": REFRESH_TOKEN}),
    })
    plugin = SimpleNamespace(logout=AsyncMock(return_value=provider_ended_session))

    monkeypatch.setattr(auth_logic, "get_redis_client", AsyncMock(return_value=redis))
    monkeypatch.setattr(auth_logic, "get_plugin_registry", lambda: _FakeRegistry(plugin))
    monkeypatch.setattr(auth_logic, "release_login_seat", AsyncMock())
    monkeypatch.setattr(auth_logic, "invalidate_principal_cache_for_token", AsyncMock())

    response = await auth_logic.logout_session(
        access_token="api-session-token", principal=SimpleNamespace(user_id="user-1"), db=None
    )

    plugin.logout.assert_awaited_once_with(ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)
    assert token_key not in redis.data
    assert response.provider == "keycloak"
