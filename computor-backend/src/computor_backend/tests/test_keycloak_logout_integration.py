"""Behavioral test for KeycloakAuthPlugin.logout() against a real Keycloak (computor-org/issues#419).

Asserts what logout is for: after ``logout(access, refresh)`` Keycloak rejects the
old refresh token with ``invalid_grant``, while a fresh login still works.

Skipped unless ``KEYCLOAK_LOGOUT_IT_URL`` points at a Keycloak whose master realm
admin can be reached with ``KEYCLOAK_LOGOUT_IT_ADMIN_USER``/``_PASSWORD`` (default
admin/admin). The test creates and deletes its own throwaway realm. For example:

    docker run -d -p 8180:8080 -e KC_BOOTSTRAP_ADMIN_USERNAME=admin \\
        -e KC_BOOTSTRAP_ADMIN_PASSWORD=admin keycloak/keycloak:26.7.4 start-dev
    KEYCLOAK_LOGOUT_IT_URL=http://localhost:8180 pytest test_keycloak_logout_integration.py
"""

import os
import uuid

import httpx
import pytest

from computor_backend.auth.keycloak import KeycloakAuthPlugin
from computor_backend.plugins.base import PluginConfig


KEYCLOAK_URL = os.environ.get("KEYCLOAK_LOGOUT_IT_URL", "").rstrip("/")
ADMIN_USER = os.environ.get("KEYCLOAK_LOGOUT_IT_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("KEYCLOAK_LOGOUT_IT_ADMIN_PASSWORD", "admin")

CLIENT_ID = "computor-backend"
CLIENT_SECRET = "logout-it-secret"
USERNAME = "logout-it-user"
PASSWORD = "logout-it-password"

pytestmark = pytest.mark.skipif(not KEYCLOAK_URL, reason="KEYCLOAK_LOGOUT_IT_URL not set")


@pytest.fixture
def realm():
    """Create a throwaway realm with a confidential client and one user."""
    name = f"logout-it-{uuid.uuid4().hex[:8]}"
    with httpx.Client(base_url=KEYCLOAK_URL, timeout=30) as client:
        admin_token = client.post(
            "/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": ADMIN_USER,
                "password": ADMIN_PASSWORD,
            },
        ).raise_for_status().json()["access_token"]
        headers = {"Authorization": f"Bearer {admin_token}"}

        client.post("/admin/realms", headers=headers, json={
            "realm": name,
            "enabled": True,
            "clients": [{
                "clientId": CLIENT_ID,
                "secret": CLIENT_SECRET,
                "enabled": True,
                "publicClient": False,
                "directAccessGrantsEnabled": True,
                "standardFlowEnabled": True,
                "redirectUris": ["http://localhost/*"],
            }],
            "users": [{
                "username": USERNAME,
                "enabled": True,
                "email": f"{USERNAME}@example.org",
                "emailVerified": True,
                "firstName": "Logout",
                "lastName": "Test",
                "credentials": [{"type": "password", "value": PASSWORD, "temporary": False}],
            }],
        }).raise_for_status()
        try:
            yield name
        finally:
            client.delete(f"/admin/realms/{name}", headers=headers)


def _token_endpoint(realm_name):
    return f"{KEYCLOAK_URL}/realms/{realm_name}/protocol/openid-connect/token"


def _password_grant(realm_name):
    response = httpx.post(_token_endpoint(realm_name), data={
        "grant_type": "password",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "username": USERNAME,
        "password": PASSWORD,
        "scope": "openid",
    })
    response.raise_for_status()
    return response.json()


def _refresh_grant(realm_name, refresh_token):
    return httpx.post(_token_endpoint(realm_name), data={
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token,
    })


async def _plugin(realm_name):
    plugin = KeycloakAuthPlugin(PluginConfig(settings={
        "server_url": KEYCLOAK_URL,
        "realm": realm_name,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }))
    await plugin.initialize()
    return plugin


def _assert_refresh_rejected(realm_name, refresh_token):
    response = _refresh_grant(realm_name, refresh_token)
    assert response.status_code == 400, response.text
    assert response.json()["error"] == "invalid_grant"


@pytest.mark.asyncio
async def test_bearer_only_end_session_post_leaves_session_alive(realm):
    """The request the old logout() sent. Keeps the rejection checks below honest:
    if this ever starts ending the session, the setup no longer reproduces #419."""
    tokens = _password_grant(realm)
    plugin = await _plugin(realm)

    httpx.post(
        plugin._oidc_config["end_session_endpoint"],
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert _refresh_grant(realm, tokens["refresh_token"]).status_code == 200


@pytest.mark.asyncio
async def test_logout_invalidates_refresh_token(realm):
    tokens = _password_grant(realm)
    plugin = await _plugin(realm)

    assert await plugin.logout(tokens["access_token"], tokens["refresh_token"]) is True

    _assert_refresh_rejected(realm, tokens["refresh_token"])
    # Logging out ends this session, not the account.
    assert _password_grant(realm)["refresh_token"]


@pytest.mark.asyncio
async def test_revocation_fallback_invalidates_refresh_token(realm):
    """Without an end-session endpoint the refresh token is revoked instead."""
    tokens = _password_grant(realm)
    plugin = await _plugin(realm)
    plugin._oidc_config = {k: v for k, v in plugin._oidc_config.items() if k != "end_session_endpoint"}

    assert await plugin.logout(tokens["access_token"], tokens["refresh_token"]) is True

    _assert_refresh_rejected(realm, tokens["refresh_token"])
    assert _password_grant(realm)["refresh_token"]


@pytest.mark.asyncio
async def test_logout_without_refresh_token_reports_failure_honestly(realm):
    tokens = _password_grant(realm)
    plugin = await _plugin(realm)

    assert await plugin.logout(tokens["access_token"]) is False
    # It did nothing, and says so: the session is still alive.
    assert _refresh_grant(realm, tokens["refresh_token"]).status_code == 200
