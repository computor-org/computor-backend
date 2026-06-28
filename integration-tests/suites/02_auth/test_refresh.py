"""POST /auth/refresh/local — returns a fresh access token."""

from __future__ import annotations

import httpx
import pytest

pytestmark = pytest.mark.auth


def test_refresh_returns_new_access_token(
    anonymous_client: httpx.Client, admin_refresh_token: str
) -> None:
    r = anonymous_client.post("/auth/refresh/local", json={"refresh_token": admin_refresh_token})
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body["access_token"], str) and body["access_token"]
    assert body["token_type"] == "Bearer"
    assert body["expires_in"] == 3600


def test_refresh_with_invalid_token_rejected(anonymous_client: httpx.Client) -> None:
    r = anonymous_client.post(
        "/auth/refresh/local", json={"refresh_token": "not-a-valid-refresh-token"}
    )
    assert r.status_code in (400, 401, 403), r.text


def test_refresh_missing_body_returns_validation_error(anonymous_client: httpx.Client) -> None:
    # See note in test_login: backend returns 400 (VAL_001) for validation
    # errors rather than FastAPI's default 422.
    r = anonymous_client.post("/auth/refresh/local", json={})
    assert r.status_code == 400
