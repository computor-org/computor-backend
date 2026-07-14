"""Unit tests for KeycloakAuthPlugin token handling.

Regression coverage for the bug where ``refresh_token()`` / ``authenticate()``
discarded the tokens they had just fetched and instead re-ran an authorization-code
exchange with an empty code (``handle_callback("", "")``). Keycloak always rejects an
empty code, so every refresh returned FAILED and the provider's rotated refresh token
never reached the caller.

Fully mocked — no live Keycloak and no JWT signing. The HTTP layer and the JWKS-based
ID-token verification are stubbed so the tests exercise only the plugin's control flow.
"""

import json
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from computor_backend.auth import keycloak as keycloak_module
from computor_backend.auth.keycloak import KeycloakAuthPlugin
from computor_backend.plugins.base import AuthStatus

# Quarantined from the default run — requires a live Keycloak (run with -m keycloak).
pytestmark = pytest.mark.keycloak


TOKEN_ENDPOINT = "https://keycloak.example/realms/computor/protocol/openid-connect/token"

# Claims the (mocked) ID-token verification yields for every grant.
FAKE_CLAIMS = {
    "sub": "user-uuid-123",
    "email": "ada@example.org",
    "preferred_username": "ada",
    "given_name": "Ada",
    "family_name": "Lovelace",
    "name": "Ada Lovelace",
    "exp": 4102444800,  # 2100-01-01, comfortably in the future
    "email_verified": True,
    "realm_access": {"roles": ["user"]},
    "resource_access": {},
}


class _FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code
        self.text = json.dumps(json_data)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "error",
                request=httpx.Request("POST", TOKEN_ENDPOINT),
                response=httpx.Response(self.status_code),
            )

    def json(self):
        return self._json


class _FakeAsyncClient:
    """Stand-in for httpx.AsyncClient: records the POST and returns a canned response."""

    def __init__(self, response, capture):
        self._response = response
        self._capture = capture

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, data=None, headers=None):
        self._capture["url"] = url
        self._capture["data"] = data
        return self._response


@contextmanager
def _mock_token_post(token_response):
    """Patch httpx.AsyncClient so any token POST returns ``token_response``; yields the capture dict."""
    capture = {}
    fake_response = _FakeResponse(token_response)
    with patch.object(
        keycloak_module.httpx,
        "AsyncClient",
        lambda *a, **k: _FakeAsyncClient(fake_response, capture),
    ):
        yield capture


def _make_plugin():
    """A plugin wired for unit testing: OIDC config injected, network + JWT verify stubbed."""
    plugin = KeycloakAuthPlugin()
    plugin._available = True
    plugin._oidc_config = {"token_endpoint": TOKEN_ENDPOINT}
    # Stub JWKS-based verification — we don't mint real signed JWTs in a unit test.
    plugin._verify_and_decode_token = AsyncMock(return_value=dict(FAKE_CLAIMS))
    # The old bug routed refresh/password grants back through the auth-code exchange.
    # Spy on it so we can assert it is never touched on those paths.
    plugin._exchange_code_for_tokens = AsyncMock()
    return plugin


@pytest.mark.asyncio
async def test_refresh_token_returns_rotated_tokens_without_reexchanging_code():
    plugin = _make_plugin()
    token_response = {
        "access_token": "new-access-token",
        "refresh_token": "rotated-refresh-token",
        "id_token": "new-id-token",
        "token_type": "Bearer",
        "expires_in": 300,
        "scope": "openid",
    }

    with _mock_token_post(token_response) as capture:
        result = await plugin.refresh_token("old-refresh-token")

    # The grant succeeded and the rotated tokens are surfaced (the heart of the bug report).
    assert result.status == AuthStatus.SUCCESS, result.error_message
    assert result.access_token == "new-access-token"
    assert result.refresh_token == "rotated-refresh-token"
    assert result.user_info.provider_id == "user-uuid-123"

    # It used the refresh_token grant carrying the supplied token...
    assert capture["data"]["grant_type"] == "refresh_token"
    assert capture["data"]["refresh_token"] == "old-refresh-token"
    # ...and never re-ran an authorization-code exchange (the regression we fixed).
    plugin._exchange_code_for_tokens.assert_not_called()


@pytest.mark.asyncio
async def test_refresh_token_reports_failure_when_provider_rejects():
    """A 4xx from the token endpoint surfaces as FAILED, not a silent success."""
    plugin = _make_plugin()
    fake_response = _FakeResponse({"error": "invalid_grant"}, status_code=400)
    with patch.object(
        keycloak_module.httpx,
        "AsyncClient",
        lambda *a, **k: _FakeAsyncClient(fake_response, {}),
    ):
        result = await plugin.refresh_token("expired-refresh-token")

    assert result.status == AuthStatus.FAILED
    plugin._exchange_code_for_tokens.assert_not_called()


@pytest.mark.asyncio
async def test_authenticate_builds_result_from_password_grant_tokens():
    plugin = _make_plugin()
    token_response = {
        "access_token": "pw-access-token",
        "refresh_token": "pw-refresh-token",
        "id_token": "pw-id-token",
        "token_type": "Bearer",
        "expires_in": 300,
    }

    with _mock_token_post(token_response) as capture:
        result = await plugin.authenticate({"username": "ada", "password": "secret"})

    assert result.status == AuthStatus.SUCCESS, result.error_message
    assert result.access_token == "pw-access-token"
    assert result.refresh_token == "pw-refresh-token"
    assert capture["data"]["grant_type"] == "password"
    plugin._exchange_code_for_tokens.assert_not_called()


@pytest.mark.asyncio
async def test_handle_callback_builds_result_from_exchanged_tokens():
    """The shared-helper refactor must not regress the login (authorization-code) path."""
    plugin = KeycloakAuthPlugin()
    plugin._available = True
    plugin._oidc_config = {"token_endpoint": TOKEN_ENDPOINT}
    plugin._verify_and_decode_token = AsyncMock(return_value=dict(FAKE_CLAIMS))
    plugin._exchange_code_for_tokens = AsyncMock(
        return_value={
            "access_token": "cb-access-token",
            "refresh_token": "cb-refresh-token",
            "id_token": "cb-id-token",
            "token_type": "Bearer",
            "expires_in": 300,
        }
    )

    result = await plugin.handle_callback("auth-code", "state", "https://app/callback")

    assert result.status == AuthStatus.SUCCESS, result.error_message
    assert result.access_token == "cb-access-token"
    assert result.refresh_token == "cb-refresh-token"
    # id_token is retained for logout's id_token_hint.
    assert result.session_data["id_token"] == "cb-id-token"
    plugin._exchange_code_for_tokens.assert_awaited_once_with("auth-code", "https://app/callback")
