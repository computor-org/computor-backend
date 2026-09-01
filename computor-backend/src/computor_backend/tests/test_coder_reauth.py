"""Tests for the #379 workspace-tab recovery endpoints.

/auth/coder-reauth renews a workspace tab's session (the tab is pure
code-server, so unlike the web UI it can never call /auth/refresh itself), and
/auth/workspace-unavailable is where the workspace ingress rewrites paths whose
workspace container is stopped. Together they turn the old dead ends (bare 401
after cookie expiry, bare 403 after auto-stop) into redirects that land the
user back inside a running workspace.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from computor_backend.api.auth import coder_reauth, workspace_unavailable
from computor_backend.exceptions import BadRequestException, UnauthorizedException
from computor_backend.permissions.principal import Principal


class _FakeRequest:
    def __init__(self, cookies=None, headers=None, method="GET"):
        self.cookies = cookies or {}
        self.headers = headers or {}
        self.method = method


_NAV_HEADERS = {"Accept": "text/html,application/xhtml+xml"}

NEXT = "/coder/uowner123/workspace/some/path?foo=bar"

REFRESH_RESULT = {
    "access_token": "new-session-token",
    "expires_in": 86400,
    "refresh_token": "rotated-refresh-token",
}


def _set_cookies(response):
    return [v.decode() for (k, v) in response.raw_headers if k == b"set-cookie"]


# --- coder-reauth -----------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_next",
    [
        "https://evil.example/coder/u1/ws",  # absolute URL
        "//evil.example/coder/u1/ws",        # protocol-relative
        "/somewhere/else",                   # not a workspace path
        "/coder/onlyowner",                  # no workspace segment
        "/coder/u1/ws\r\nSet-Cookie: x=y",   # header injection in the tail
    ],
)
async def test_reauth_rejects_non_workspace_next(bad_next):
    with pytest.raises(BadRequestException):
        await coder_reauth(_FakeRequest(), bad_next, False, Principal(user_id="u1"), MagicMock())


@pytest.mark.asyncio
async def test_reauth_with_live_session_bounces_straight_back():
    with patch("computor_backend.api.auth._workspace_public_origin", return_value="http://ws.example"):
        resp = await coder_reauth(_FakeRequest(), NEXT, False, Principal(user_id="u1"), MagicMock())
    assert resp.status_code == 302
    assert resp.headers["location"] == f"http://ws.example{NEXT}"


@pytest.mark.asyncio
async def test_reauth_renews_session_from_refresh_cookie():
    request = _FakeRequest(cookies={"ct_refresh_token": "cookie-refresh-token"})
    with patch("computor_backend.business_logic.auth.refresh_sso_token",
               new=AsyncMock(return_value=REFRESH_RESULT)) as mock_refresh, \
         patch("computor_backend.api.auth._workspace_public_origin", return_value=""):
        resp = await coder_reauth(request, NEXT, False, None, MagicMock())

    # The refresh token is the credential here — there is no principal to check.
    assert mock_refresh.await_args.kwargs["refresh_token"] == "cookie-refresh-token"
    assert mock_refresh.await_args.kwargs["principal"] is None
    assert resp.status_code == 302
    assert resp.headers["location"] == NEXT
    cookies = _set_cookies(resp)
    assert any(c.startswith("ct_access_token=new-session-token") for c in cookies)
    assert any(c.startswith("ct_refresh_token=rotated-refresh-token") for c in cookies)
    assert all("HttpOnly" in c for c in cookies)


@pytest.mark.asyncio
async def test_reauth_falls_back_to_sso_login_when_refresh_fails():
    request = _FakeRequest(cookies={"ct_refresh_token": "stale-token"})
    with patch("computor_backend.business_logic.auth.refresh_sso_token",
               new=AsyncMock(side_effect=UnauthorizedException(detail="expired"))), \
         patch("computor_backend.api.auth._default_sso_provider", return_value="keycloak"):
        resp = await coder_reauth(request, NEXT, False, None, MagicMock())

    assert resp.status_code == 302
    location = resp.headers["location"]
    assert "/auth/keycloak/login?" in location
    # The login round-trip returns here with retried=true, so a second failure
    # cannot loop the browser.
    assert "redirect_uri=" in location and "retried%3Dtrue" in location


@pytest.mark.asyncio
async def test_reauth_without_any_credential_redirects_to_login():
    with patch("computor_backend.api.auth._default_sso_provider", return_value="keycloak"):
        resp = await coder_reauth(_FakeRequest(), NEXT, False, None, MagicMock())
    assert resp.status_code == 302
    assert "/auth/keycloak/login?" in resp.headers["location"]


@pytest.mark.asyncio
async def test_reauth_after_failed_login_roundtrip_stops_looping():
    with pytest.raises(UnauthorizedException):
        await coder_reauth(_FakeRequest(), NEXT, True, None, MagicMock())


# --- workspace-unavailable --------------------------------------------------


@pytest.mark.asyncio
async def test_stopped_workspace_navigation_goes_to_launch_page():
    with patch("computor_backend.api.auth._web_app_base", return_value="http://web.example"):
        resp = await workspace_unavailable(_FakeRequest(headers=_NAV_HEADERS), "uowner123", "workspace")
    assert resp.status_code == 302
    assert resp.headers["location"] == "http://web.example/workspaces/launch?owner=uowner123&name=workspace"


@pytest.mark.asyncio
async def test_stopped_workspace_xhr_gets_503():
    resp = await workspace_unavailable(_FakeRequest(headers={"Accept": "*/*"}), "uowner123", "workspace")
    assert resp.status_code == 503
