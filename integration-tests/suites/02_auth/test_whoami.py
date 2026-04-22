"""GET /users (current user) — returns admin when authed, 401 when not.

`/users` without an ID is the "whoami" endpoint in this API.
"""

from __future__ import annotations

import httpx
import pytest

pytestmark = pytest.mark.auth


def test_whoami_with_bearer_token(
    admin_client: httpx.Client, admin_credentials: dict[str, str]
) -> None:
    r = admin_client.get("/users")
    assert r.status_code == 200, r.text
    user = r.json()
    assert user["username"] == admin_credentials["username"]


def test_whoami_with_basic_auth(
    admin_basic_client: httpx.Client, admin_credentials: dict[str, str]
) -> None:
    r = admin_basic_client.get("/users")
    assert r.status_code == 200, r.text
    assert r.json()["username"] == admin_credentials["username"]


def test_whoami_anonymous_returns_401(anonymous_client: httpx.Client) -> None:
    r = anonymous_client.get("/users")
    assert r.status_code == 401


def test_whoami_with_bogus_bearer_returns_401(
    api_base_url: str,
) -> None:
    with httpx.Client(
        base_url=api_base_url, headers={"Authorization": "Bearer not-a-real-token"}
    ) as c:
        r = c.get("/users")
    assert r.status_code == 401
