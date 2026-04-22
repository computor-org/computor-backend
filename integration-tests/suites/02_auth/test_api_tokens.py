"""API token (ctp_*) lifecycle: create → use via X-API-Token → revoke.

Session-scoped: the token created here persists for later suites if
they want to reuse it (store on request.config.stash or similar once
that pattern is needed).
"""

from __future__ import annotations

import httpx
import pytest

from fixtures.api import api_token_client

pytestmark = pytest.mark.auth


@pytest.fixture(scope="session")
def admin_api_token(
    admin_client: httpx.Client,
) -> dict[str, object]:
    r = admin_client.post(
        "/api-tokens",
        json={
            "name": "integration-test-admin",
            "description": "created by M2 auth tests",
            "scopes": [],
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_api_token_creation_returns_plaintext_once(admin_api_token: dict[str, object]) -> None:
    token = admin_api_token["token"]
    assert isinstance(token, str) and token.startswith("ctp_")
    assert admin_api_token["token_prefix"] == token[:12]
    assert admin_api_token["name"] == "integration-test-admin"


def test_api_token_authenticates_via_x_api_token_header(
    api_base_url: str, admin_api_token: dict[str, object], admin_credentials: dict[str, str]
) -> None:
    with api_token_client(api_base_url, admin_api_token["token"]) as c:  # type: ignore[arg-type]
        r = c.get("/users")
    assert r.status_code == 200, r.text
    assert r.json()["username"] == admin_credentials["username"]


def test_api_tokens_list_includes_created(
    admin_client: httpx.Client, admin_api_token: dict[str, object]
) -> None:
    r = admin_client.get("/api-tokens")
    assert r.status_code == 200, r.text
    ids = {entry["id"] for entry in r.json()}
    assert admin_api_token["id"] in ids


def test_api_token_revocation_invalidates_token(
    api_base_url: str, admin_client: httpx.Client
) -> None:
    # Create a throwaway token so we don't nuke the session-scoped one.
    create = admin_client.post(
        "/api-tokens",
        json={"name": "throwaway-revoke-target", "scopes": []},
    )
    assert create.status_code == 201, create.text
    created = create.json()

    delete = admin_client.delete(f"/api-tokens/{created['id']}")
    assert delete.status_code == 204, delete.text

    with api_token_client(api_base_url, created["token"]) as c:
        r = c.get("/users")
    assert r.status_code == 401


def test_bad_api_token_rejected(api_base_url: str) -> None:
    with api_token_client(api_base_url, "ctp_obviously-not-a-real-token") as c:
        r = c.get("/users")
    assert r.status_code == 401
