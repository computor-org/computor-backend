"""Signing out of the web app ends the Keycloak session, too.

The web app logs out by browser-navigating to ``/auth/keycloak/logout``, which
forwards to Keycloak's end-session endpoint. Keycloak ends its session there
without asking only when it gets an ``id_token_hint``; the session written by a
token refresh dropped the id_token, so after the first refresh Keycloak stopped
at "Do you want to log out?" and a user who left that page stayed signed in —
the next sign-in silently returned the same account.

Fully mocked: in-memory Redis, a stub provider plugin and a mock database.
"""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from urllib.parse import parse_qs, urlsplit

import pytest
from starlette.requests import Request

from computor_backend.api import auth
from computor_backend.business_logic import auth as auth_logic
from computor_backend.plugins import AuthStatus
from computor_backend.utils.token_hash import hash_token

ACCESS = "sso_access_7c1e9a04b2d6"
USER_ID = "5f0b6a2e-31c4-4d7a-9e18-2b7c0d4f9a11"
TOKEN_KEY = f"sso_token:keycloak:{USER_ID}"


class _Redis:
    def __init__(self):
        self.data = {}

    async def set(self, key, value, **kwargs):
        self.data[key] = value

    async def get(self, key):
        await asyncio.sleep(0)
        return self.data.get(key)

    async def delete(self, key):
        return self.data.pop(key, None)


def _request(cookie=""):
    headers = [(b"cookie", cookie.encode())] if cookie else []
    return Request({
        "type": "http", "method": "GET", "scheme": "https",
        "server": ("computor.at", 443), "client": ("127.0.0.1", 12345),
        "path": "/", "query_string": b"", "headers": headers, "app": None,
    })


def _plugin(logout_result=True):
    plugin = Mock()
    plugin._oidc_config = {"end_session_endpoint": "https://idp.invalid/logout"}
    plugin.logout = AsyncMock(return_value=logout_result)
    return plugin


async def _logout(redis, plugin, cookie=f"ct_access_token={ACCESS}"):
    registry = Mock()
    registry.get_plugin.return_value = plugin
    with patch.object(auth, "get_plugin_registry", return_value=registry):
        return await auth.sso_logout("keycloak", _request(cookie), "https://computor.at/", redis)


def _signed_in(redis, id_token=None):
    redis.data[f"sso_session:{hash_token(ACCESS)}"] = json.dumps(
        {"user_id": USER_ID, "provider": "keycloak", "id_token": id_token}
    )
    redis.data[TOKEN_KEY] = json.dumps(
        {"access_token": "kc-access", "refresh_token": "kc-refresh"}
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("id_token", [None, "kc-id-token"])
async def test_logout_ends_the_keycloak_session_server_side(id_token):
    redis, plugin = _Redis(), _plugin()
    _signed_in(redis, id_token)

    resp = await _logout(redis, plugin)

    plugin.logout.assert_awaited_once_with("kc-access", refresh_token="kc-refresh")
    assert TOKEN_KEY not in redis.data
    assert f"sso_session:{hash_token(ACCESS)}" not in redis.data
    params = parse_qs(urlsplit(resp.headers["location"]).query)
    assert params.get("id_token_hint") == ([id_token] if id_token else None)


@pytest.mark.asyncio
@pytest.mark.parametrize("plugin_logout", [
    AsyncMock(return_value=False),
    AsyncMock(side_effect=RuntimeError("keycloak down")),
])
async def test_logout_still_clears_cookies_when_the_provider_does_not_confirm(plugin_logout):
    redis, plugin = _Redis(), _plugin()
    plugin.logout = plugin_logout
    _signed_in(redis)

    resp = await _logout(redis, plugin)

    assert resp.status_code == 302
    cookies = resp.headers.getlist("set-cookie")
    assert any("ct_access_token=" in c for c in cookies)
    assert any("ct_refresh_token=" in c for c in cookies)


@pytest.mark.asyncio
async def test_logout_without_a_session_touches_no_provider_tokens():
    redis, plugin = _Redis(), _plugin()
    redis.data[TOKEN_KEY] = json.dumps({"access_token": "a", "refresh_token": "r"})

    await _logout(redis, plugin, cookie="")

    plugin.logout.assert_not_awaited()
    assert TOKEN_KEY in redis.data


@pytest.mark.asyncio
async def test_refreshed_session_keeps_the_id_token_for_logout():
    redis = _Redis()
    plugin = Mock()
    plugin.refresh_token = AsyncMock(return_value=SimpleNamespace(
        status=AuthStatus.SUCCESS,
        user_info=SimpleNamespace(provider_id="kc-sub"),
        access_token="kc-access-2",
        refresh_token="kc-refresh-2",
        expires_at=None,
        session_data={"id_token": "kc-id-token-2"},
    ))
    registry = Mock()
    registry.get_enabled_plugins.return_value = ["keycloak"]
    registry.ensure_plugin_ready = AsyncMock(return_value=plugin)
    user = SimpleNamespace(id=USER_ID, email="ada@example.org")
    account = SimpleNamespace(id="acc-1", user=user)
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = account

    with patch.object(auth_logic, "get_plugin_registry", return_value=registry), \
         patch.object(auth_logic, "get_redis_client", AsyncMock(return_value=redis)), \
         patch.object(auth_logic, "touch_login_seat", AsyncMock()), \
         patch.object(auth_logic, "login_idle_seconds", Mock(return_value=900)):
        result = await auth_logic.refresh_sso_token("kc-refresh", "keycloak", None, db)

    session = json.loads(redis.data[f"sso_session:{hash_token(result['access_token'])}"])
    assert session["id_token"] == "kc-id-token-2"
    assert session["user_id"] == USER_ID
