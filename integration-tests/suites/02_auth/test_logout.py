"""POST /auth/logout — token is invalidated afterwards.

Logs in with a dedicated second admin session so the shared
`admin_access_token` stays usable for other suites.
"""

from __future__ import annotations

import httpx
import pytest

from fixtures.api import bearer_client

pytestmark = pytest.mark.auth


def test_logout_revokes_token(
    anonymous_client: httpx.Client,
    api_base_url: str,
    admin_credentials: dict[str, str],
) -> None:
    # Fresh login so other tests' tokens are unaffected.
    login = anonymous_client.post("/auth/login", json=admin_credentials)
    assert login.status_code == 200, login.text
    access = login.json()["access_token"]

    with bearer_client(api_base_url, access) as c:
        pre = c.get("/users")
        assert pre.status_code == 200, pre.text

        out = c.post("/auth/logout")
        assert out.status_code == 200, out.text

        post = c.get("/users")
        assert post.status_code == 401
