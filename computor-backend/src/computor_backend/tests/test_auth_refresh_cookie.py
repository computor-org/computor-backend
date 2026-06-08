"""Tests for the /auth/refresh cookie behavior.

The web UI calls /auth/refresh with no refresh_token in the body, relying on the
HttpOnly ct_refresh_token cookie, and expects the backend to renew the HttpOnly
cookies. These tests pin both: cookie fallback for the refresh token, and
re-setting ct_access_token / ct_refresh_token on success.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Response

from computor_backend.api.auth import refresh_token
from computor_backend.exceptions import UnauthorizedException
from computor_backend.permissions.principal import Principal
from computor_types.auth import TokenRefreshRequest


class _Req:
    def __init__(self, cookies):
        self.cookies = cookies


def _set_cookies(response):
    return [v.decode() for (k, v) in response.raw_headers if k == b"set-cookie"]


REFRESH_RESULT = {
    "access_token": "new-session-token",
    "expires_in": 86400,
    "refresh_token": "rotated-refresh-token",
}


@pytest.mark.asyncio
async def test_refresh_falls_back_to_cookie_and_renews_cookies():
    body = TokenRefreshRequest(provider="keycloak")  # no refresh_token in body
    request = _Req({"ct_refresh_token": "cookie-refresh-token"})
    response = Response()
    principal = Principal(user_id="u1")

    with patch("computor_backend.business_logic.auth.refresh_sso_token",
               new=AsyncMock(return_value=REFRESH_RESULT)) as mock_refresh:
        result = await refresh_token(body, request, response, principal, MagicMock())

    # Used the cookie's refresh token, not the (absent) body value.
    assert mock_refresh.await_args.kwargs["refresh_token"] == "cookie-refresh-token"
    # Renewed both HttpOnly cookies.
    cookies = _set_cookies(response)
    assert any(c.startswith("ct_access_token=new-session-token") for c in cookies)
    assert any(c.startswith("ct_refresh_token=rotated-refresh-token") for c in cookies)
    assert all("HttpOnly" in c for c in cookies)
    assert result.access_token == "new-session-token"


@pytest.mark.asyncio
async def test_refresh_prefers_body_token_when_present():
    body = TokenRefreshRequest(refresh_token="body-refresh-token", provider="keycloak")
    request = _Req({"ct_refresh_token": "cookie-refresh-token"})
    response = Response()

    with patch("computor_backend.business_logic.auth.refresh_sso_token",
               new=AsyncMock(return_value=REFRESH_RESULT)) as mock_refresh:
        await refresh_token(body, request, response, Principal(user_id="u1"), MagicMock())

    assert mock_refresh.await_args.kwargs["refresh_token"] == "body-refresh-token"


@pytest.mark.asyncio
async def test_refresh_without_any_token_is_unauthorized():
    body = TokenRefreshRequest(provider="keycloak")
    request = _Req({})  # no cookie either
    response = Response()

    with patch("computor_backend.business_logic.auth.refresh_sso_token",
               new=AsyncMock(return_value=REFRESH_RESULT)) as mock_refresh:
        with pytest.raises(UnauthorizedException):
            await refresh_token(body, request, response, Principal(user_id="u1"), MagicMock())
        mock_refresh.assert_not_awaited()
