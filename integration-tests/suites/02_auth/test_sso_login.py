"""SSO login — the only auth path now that local password login was removed.

Exercises the headless authorization-code dance (fixtures.keycloak_auth), whoami
via the resulting bearer, and rejection of bad/absent credentials.
"""

from __future__ import annotations

import httpx
import pytest

from fixtures.keycloak_auth import LoginError, authenticate

pytestmark = pytest.mark.auth


def test_admin_login_returns_working_bearer(
    api_base_url: str, admin_credentials: dict[str, str]
) -> None:
    creds = authenticate(
        admin_credentials["email"], admin_credentials["password"], api_base=api_base_url
    )
    assert creds.token and creds.user_id
    r = httpx.get(
        f"{api_base_url}/user",
        headers={"Authorization": f"Bearer {creds.token}"},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    assert r.json()["email"] == admin_credentials["email"]


def test_admin_is_recognized_as_admin(admin_client: httpx.Client) -> None:
    r = admin_client.get("/user/scopes")
    assert r.status_code == 200, r.text
    assert r.json().get("is_admin") is True


def test_wrong_password_is_rejected(
    api_base_url: str, admin_credentials: dict[str, str]
) -> None:
    with pytest.raises(LoginError):
        authenticate(admin_credentials["email"], "definitely-the-wrong-password", api_base=api_base_url)


def test_unknown_user_is_rejected(api_base_url: str) -> None:
    with pytest.raises(LoginError):
        authenticate("nobody@integration.test", "whatever-2099", api_base=api_base_url)


def test_bogus_bearer_rejected(anonymous_client: httpx.Client) -> None:
    r = anonymous_client.get("/user", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401


def test_unauthenticated_user_endpoint_401(anonymous_client: httpx.Client) -> None:
    r = anonymous_client.get("/user")
    assert r.status_code == 401
