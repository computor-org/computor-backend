"""POST /auth/login — shape of the happy path, rejection of bad creds.

Login rate-limits at 5/min per username, so this file is lean on
deliberately-wrong attempts.
"""

from __future__ import annotations

import httpx
import pytest

pytestmark = pytest.mark.auth


def test_login_returns_expected_fields(admin_login: dict[str, object]) -> None:
    assert isinstance(admin_login["access_token"], str) and admin_login["access_token"]
    assert isinstance(admin_login["refresh_token"], str) and admin_login["refresh_token"]
    assert admin_login["token_type"] == "Bearer"
    assert admin_login["expires_in"] == 3600
    assert isinstance(admin_login["user_id"], str) and admin_login["user_id"]


def test_login_wrong_password_returns_401(
    anonymous_client: httpx.Client, admin_credentials: dict[str, str]
) -> None:
    r = anonymous_client.post(
        "/auth/login",
        json={"username": admin_credentials["username"], "password": "definitely-not-the-password"},
    )
    assert r.status_code == 401, r.text


def test_login_unknown_user_returns_401(anonymous_client: httpx.Client) -> None:
    r = anonymous_client.post(
        "/auth/login",
        json={"username": "no-such-user-exists", "password": "whatever"},
    )
    assert r.status_code == 401, r.text


def test_login_missing_fields_returns_validation_error(anonymous_client: httpx.Client) -> None:
    # Backend normalises Pydantic validation errors to 400 (VAL_001) via its
    # custom exception handler — not the FastAPI default 422.
    r = anonymous_client.post("/auth/login", json={})
    assert r.status_code == 400, r.text
    body = r.json()
    assert body.get("error_code") == "VAL_001"
