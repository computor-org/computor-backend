"""KeycloakAdminClient token grant selection (service account vs admin password)."""

import asyncio

import computor_backend.auth.keycloak_admin as kc_mod

AUTOMATION = ("KEYCLOAK_AUTOMATION_CLIENT_ID", "KEYCLOAK_AUTOMATION_CLIENT_SECRET")


def _token_request(monkeypatch, **env):
    for key in (*AUTOMATION, "KEYCLOAK_ADMIN", "KEYCLOAK_ADMIN_PASSWORD"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    sent = {}

    class _Response:
        status_code = 200

        def json(self):
            return {"access_token": "tok"}

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, data=None, headers=None):
            sent["url"] = url
            sent["data"] = data
            return _Response()

    monkeypatch.setattr(kc_mod.httpx, "AsyncClient", _Client)
    client = kc_mod.KeycloakAdminClient()
    assert asyncio.run(client._get_admin_token()) == "tok"
    return sent


def test_client_credentials_when_both_automation_vars_set(monkeypatch):
    sent = _token_request(
        monkeypatch,
        KEYCLOAK_AUTOMATION_CLIENT_ID="automation",
        KEYCLOAK_AUTOMATION_CLIENT_SECRET="s3cret",
        KEYCLOAK_ADMIN="admin",
        KEYCLOAK_ADMIN_PASSWORD="pw",
    )
    assert sent["url"].endswith("/realms/master/protocol/openid-connect/token")
    assert sent["data"] == {
        "grant_type": "client_credentials",
        "client_id": "automation",
        "client_secret": "s3cret",
    }


def test_password_grant_without_automation_vars(monkeypatch):
    sent = _token_request(
        monkeypatch, KEYCLOAK_ADMIN="admin", KEYCLOAK_ADMIN_PASSWORD="pw"
    )
    assert sent["data"]["grant_type"] == "password"
    assert sent["data"]["client_id"] == "admin-cli"
    assert sent["data"]["username"] == "admin"
    assert sent["data"]["password"] == "pw"


def test_password_grant_when_only_one_automation_var_set(monkeypatch):
    sent = _token_request(monkeypatch, KEYCLOAK_AUTOMATION_CLIENT_ID="automation")
    assert sent["data"]["grant_type"] == "password"
