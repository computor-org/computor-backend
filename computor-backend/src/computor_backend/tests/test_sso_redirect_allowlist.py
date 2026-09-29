"""Open-redirect guard for SSO login, callback and logout (api/auth.py).

The callback hands a fresh session to the destination chosen when the login was
started, so an attacker-chosen redirect_uri used to receive the victim's access
and refresh tokens in its query. These tests drive the real endpoint functions
with an in-memory Redis, a mocked provider registry and a mocked identity
exchange, and use distinctive synthetic credential values.
"""

import asyncio
import json
import logging
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from urllib.parse import parse_qs, urlsplit

import pytest
from starlette.requests import Request

from computor_backend.api import auth
from computor_backend.exceptions import BadRequestException, ForbiddenException
from computor_backend.settings import settings

ACCESS = "sso_access_4b9e17c2d05a"
REFRESH = "sso_refresh_e6a3f0915c8d"
USER_ID = "0232de59-e05d-4bc2-898f-b879c06abcde"

REJECTED = [
    "https://attacker.example/collect",
    "//evil.example/collect",  # scheme-relative
    "/\\evil.example/collect",  # browsers read "\" as "/"
    "\\\\evil.example/collect",
    "https://computor.at@evil.example/collect",  # userinfo trick
    "https://computor.at:pw@evil.example/",
    "https://evil.example\\@computor.at/",
    "https://evil.example#@computor.at/",
    "HTTPS://EVIL.EXAMPLE/collect",  # mixed case, still foreign
    "https://computor.at.evil.example/",
    "http://computor.at/auth/success",  # scheme mismatch
    "https://computor.at:8443/auth/success",  # port mismatch
    "javascript:alert(1)",
    "http://localhost:4321/nonce",  # loopback receiver is 127.0.0.1 only
    "http://127.0.0.1/nonce",  # ... with an explicit port
    "https://127.0.0.1:4321/nonce",
    "/\t/evil.example",
    "relative/path",
]

ALLOWED_WEB = [
    "/auth/success",
    "https://computor.at/auth/success",
    "https://COMPUTOR.at/auth/success",  # host case is not significant
    "https://computor.at:443/auth/success",
    "https://computor.at/api/auth/coder-reauth?next=%2Fcoder%2Fu1%2Fws%2F&retried=true",
    "https://code.tugraz.at/auth/success",  # per-deployment extra origin
]

LOOPBACK = "http://127.0.0.1:53817/0f1e2d3c4b5a69788796a5b4c3d2e1f0"


@pytest.fixture(autouse=True)
def deployment(monkeypatch):
    monkeypatch.setattr(settings, "PUBLIC_DOMAIN", "https://computor.at", raising=False)
    monkeypatch.setattr(settings, "WEB_APP_URL", None, raising=False)
    monkeypatch.setattr(
        settings, "SSO_REDIRECT_ALLOWED_ORIGINS", "https://code.tugraz.at", raising=False
    )
    monkeypatch.setattr(settings, "DEBUG_MODE", "production", raising=False)
    monkeypatch.setenv("NEXT_PUBLIC_API_URL", "https://computor.at/api")


class _Redis:
    def __init__(self):
        self.data = {}

    async def set(self, key, value, **kwargs):
        self.data[key] = value

    async def get(self, key):
        value = self.data.get(key)
        await asyncio.sleep(0)  # a network round-trip: other requests interleave
        return value

    async def getdel(self, key):
        return self.data.pop(key, None)  # atomic, like Redis GETDEL

    async def delete(self, key):
        return self.data.pop(key, None)


def _request():
    return Request({
        "type": "http", "method": "GET", "scheme": "https",
        "server": ("computor.at", 443), "client": ("127.0.0.1", 12345),
        "path": "/", "query_string": b"", "headers": [], "app": None,
    })


def _registry():
    registry = Mock()
    registry.get_enabled_plugins.return_value = ["keycloak"]
    registry.ensure_plugin_ready = AsyncMock(return_value=object())
    registry.get_login_url.side_effect = (
        lambda provider, callback, state: f"https://idp.invalid/authorize?state={state}"
    )
    return registry


async def _initiate(redirect_uri, redis):
    with patch.object(auth, "get_plugin_registry", return_value=_registry()), \
         patch("computor_backend.redis_cache.get_redis_client", AsyncMock(return_value=redis)):
        return await auth.initiate_login("keycloak", redirect_uri, _request())


async def _callback(redis, state, exchange=None):
    exchange = exchange or AsyncMock(return_value={
        "user_id": USER_ID, "account_id": "acc-1", "is_new_user": False,
        "token": ACCESS, "refresh_token": REFRESH,
    })
    with patch("computor_backend.redis_cache.get_redis_client", AsyncMock(return_value=redis)), \
         patch("computor_backend.business_logic.auth.handle_sso_callback", exchange):
        return await auth.handle_callback("keycloak", "idp-code", state, _request(), Mock())


def _plant_state(redis, redirect_uri, state="planted-state"):
    redis.data[f"sso_state:{state}"] = json.dumps(
        {"provider": "keycloak", "redirect_uri": redirect_uri}
    )
    return state


def _assert_first_party(location):
    parts = urlsplit(location)
    assert parts.netloc in ("", "computor.at"), location
    assert not location.startswith("//") and "\\" not in location


# --- login initiation ------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("redirect_uri", REJECTED)
async def test_login_rejects_foreign_redirect(redirect_uri):
    redis = _Redis()
    with pytest.raises(BadRequestException) as exc:
        await _initiate(redirect_uri, redis)
    assert exc.value.status_code == 400
    assert not redis.data  # nothing stored for the callback to act on


@pytest.mark.asyncio
@pytest.mark.parametrize("redirect_uri", ALLOWED_WEB + [LOOPBACK])
async def test_login_accepts_first_party_and_loopback_redirect(redirect_uri):
    # Compatibility guard (passes before and after the fix): the web app, the
    # coder-reauth hop and the VS Code loopback receiver keep working.
    redis = _Redis()
    resp = await _initiate(redirect_uri, redis)
    assert resp.status_code == 302
    (stored,) = redis.data.values()
    assert json.loads(stored)["redirect_uri"] == redirect_uri


# --- callback --------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("redirect_uri", REJECTED)
async def test_callback_never_sends_session_to_a_planted_foreign_target(redirect_uri):
    # State written before the initiation check existed (or by any other path)
    # must not choose the destination either.
    redis = _Redis()
    resp = await _callback(redis, _plant_state(redis, redirect_uri))
    location = resp.headers["location"]
    _assert_first_party(location)
    assert ACCESS not in location and REFRESH not in location


@pytest.mark.asyncio
async def test_attacker_initiated_login_cannot_steal_tokens():
    # The reviewer's reproduction: attacker-built login link, victim completes it.
    redis = _Redis()
    with pytest.raises(BadRequestException):
        await _initiate("https://attacker.invalid/collect", redis)
    assert not redis.data


@pytest.mark.asyncio
@pytest.mark.parametrize("redirect_uri", ALLOWED_WEB)
async def test_callback_keeps_tokens_out_of_web_redirects(redirect_uri):
    # The web app and coder-reauth authenticate via the HttpOnly cookies; the
    # tokens must not ride along in a browser-visible URL.
    redis = _Redis()
    resp = await _callback(redis, _plant_state(redis, redirect_uri))
    location = resp.headers["location"]
    assert location.startswith(redirect_uri)
    assert ACCESS not in location and REFRESH not in location
    cookies = "\n".join(resp.headers.getlist("set-cookie"))
    assert f"ct_access_token={ACCESS}" in cookies
    assert f"ct_refresh_token={REFRESH}" in cookies


@pytest.mark.asyncio
async def test_callback_hands_tokens_to_the_extension_loopback_receiver():
    # Compatibility guard: computor-vscode SsoLoginService reads token and
    # refresh_token from the query of its http://127.0.0.1:<port>/<nonce> URL.
    redis = _Redis()
    resp = await _callback(redis, _plant_state(redis, LOOPBACK))
    parts = urlsplit(resp.headers["location"])
    assert f"{parts.scheme}://{parts.netloc}{parts.path}" == LOOPBACK
    params = parse_qs(parts.query)
    assert params["token"] == [ACCESS] and params["refresh_token"] == [REFRESH]


@pytest.mark.asyncio
@pytest.mark.parametrize("redirect_uri", ["https://attacker.example/x", "//evil.example/x"])
async def test_refused_sign_in_is_not_bounced_off_site(redirect_uri):
    redis = _Redis()
    refusal = AsyncMock(side_effect=ForbiddenException(detail="Instance is at capacity"))
    resp = await _callback(redis, _plant_state(redis, redirect_uri), exchange=refusal)
    _assert_first_party(resp.headers["location"])
    assert "sign_in_refused" in resp.headers["location"]


@pytest.mark.asyncio
async def test_rejected_redirect_is_not_logged_verbatim(caplog):
    # Guard for the rejection warning added with the allowlist (pre-fix code
    # logged nothing here, so this cannot fail on it).
    caplog.set_level(logging.DEBUG, logger="computor_backend.api.auth")
    redis = _Redis()
    await _callback(redis, _plant_state(redis, f"https://attacker.example/?token={ACCESS}"))
    assert ACCESS not in caplog.text and "attacker.example" not in caplog.text


# --- logout ----------------------------------------------------------------------


def _logout_registry(end_session):
    plugin = Mock()
    plugin._oidc_config = {"end_session_endpoint": end_session} if end_session else None
    registry = Mock()
    registry.get_plugin.return_value = plugin
    return registry


async def _logout(post_logout_redirect_uri, end_session=None):
    with patch.object(auth, "get_plugin_registry", return_value=_logout_registry(end_session)):
        return await auth.sso_logout("keycloak", _request(), post_logout_redirect_uri, _Redis())


@pytest.mark.asyncio
@pytest.mark.parametrize("end_session", [None, "https://idp.invalid/logout"])
@pytest.mark.parametrize("target", REJECTED + [LOOPBACK])
async def test_logout_drops_foreign_post_logout_redirect(target, end_session):
    resp = await _logout(target, end_session)
    location = resp.headers["location"]
    assert "evil.example" not in location.lower() and "attacker.example" not in location
    assert "127.0.0.1" not in location
    if end_session is None:
        _assert_first_party(location)
        assert target not in location
    else:
        assert "post_logout_redirect_uri" not in parse_qs(urlsplit(location).query)
    # Logout itself still happens.
    assert any("ct_access_token=" in c for c in resp.headers.getlist("set-cookie"))


@pytest.mark.asyncio
async def test_logout_keeps_first_party_post_logout_redirect():
    # Compatibility guard: the web app sends its own origin root.
    resp = await _logout("https://computor.at/", "https://idp.invalid/logout")
    params = parse_qs(urlsplit(resp.headers["location"]).query)
    assert params["post_logout_redirect_uri"] == ["https://computor.at/"]


# --- state handling ----------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("state", [None, ""])
async def test_callback_requires_state(state):
    # Without state nothing ties the callback to a login we started (login CSRF).
    exchange = AsyncMock()
    with pytest.raises(BadRequestException) as exc:
        await _callback(_Redis(), state, exchange=exchange)
    assert exc.value.status_code == 400
    exchange.assert_not_awaited()


@pytest.mark.asyncio
async def test_state_is_consumed_once_under_concurrent_replay():
    # Two callbacks racing on one state (a replayed redirect) must not both
    # exchange the code and both receive a session.
    redis = _Redis()
    state = _plant_state(redis, "/auth/success")
    exchange = AsyncMock(return_value={
        "user_id": USER_ID, "account_id": "acc-1", "is_new_user": False,
        "token": ACCESS, "refresh_token": REFRESH,
    })
    responses = await asyncio.gather(
        _callback(redis, state, exchange=exchange), _callback(redis, state, exchange=exchange)
    )
    assert exchange.await_count == 1
    with_session = [r for r in responses if any(
        ACCESS in c for c in r.headers.getlist("set-cookie"))]
    assert len(with_session) == 1
    assert not redis.data


# --- shipped development defaults ----------------------------------------------------


def _template_values():
    repo = Path(__file__).resolve().parents[4]
    values = {}
    for line in (repo / "ops/environments/.env.common.template").read_text().splitlines():
        key, sep, value = line.partition("=")
        if sep and not key.startswith("#"):
            values[key.strip()] = value.strip()
    return values


@pytest.fixture
def shipped_defaults(monkeypatch):
    env = _template_values()
    monkeypatch.setattr(settings, "PUBLIC_DOMAIN", env.get("PUBLIC_DOMAIN") or None)
    monkeypatch.setattr(settings, "WEB_APP_URL", env.get("WEB_APP_URL") or None)
    monkeypatch.setattr(settings, "SSO_REDIRECT_ALLOWED_ORIGINS",
                        env.get("SSO_REDIRECT_ALLOWED_ORIGINS", ""), raising=False)
    monkeypatch.setattr(settings, "DEBUG_MODE", env.get("DEBUG_MODE", "development"))
    monkeypatch.setenv("NEXT_PUBLIC_API_URL", env["NEXT_PUBLIC_API_URL"])


@pytest.mark.asyncio
async def test_dev_web_login_and_logout_work_with_shipped_defaults(shipped_defaults):
    # computor-web builds these from window.location.origin (localhost:3000 in dev).
    redis = _Redis()
    resp = await _initiate("http://localhost:3000/auth/success", redis)
    assert resp.status_code == 302
    (state_key,) = redis.data
    resp = await _callback(redis, state_key.split(":", 1)[1])
    assert resp.headers["location"].startswith("http://localhost:3000/auth/success")
    resp = await _logout("http://localhost:3000/", "https://idp.invalid/logout")
    params = parse_qs(urlsplit(resp.headers["location"]).query)
    assert params["post_logout_redirect_uri"] == ["http://localhost:3000/"]


@pytest.mark.asyncio
async def test_shipped_defaults_still_reject_foreign_origins(shipped_defaults):
    with pytest.raises(BadRequestException):
        await _initiate("http://localhost:3001/auth/success", _Redis())
