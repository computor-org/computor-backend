"""The API names Keycloak's account console for the web app's Settings (issues#485).

Settings linked it only when the web build carried NEXT_PUBLIC_KEYCLOAK_URL, and
no deployment's build did, so on computor.at users had no way from the app to
add or replace an authenticator.
"""

from types import SimpleNamespace

import pytest

from computor_backend.api import auth as auth_api
from computor_backend.auth.keycloak import KeycloakAuthPlugin


@pytest.fixture
def plugin(monkeypatch):
    monkeypatch.delenv("KEYCLOAK_PUBLIC_URL", raising=False)
    monkeypatch.setenv("KEYCLOAK_REALM", "computor")
    return KeycloakAuthPlugin()


def test_the_console_uses_the_public_base_sign_in_uses(plugin, monkeypatch):
    monkeypatch.setenv("KEYCLOAK_PUBLIC_URL", "https://computor.at/auth/")
    plugin._oidc_config = {"issuer": "http://computor-keycloak:8080/auth/realms/computor"}
    assert plugin.get_account_url() == "https://computor.at/auth/realms/computor/account/"


def test_without_a_public_base_the_issuer_names_it(plugin):
    plugin._oidc_config = {"issuer": "https://sso.example.org/realms/computor"}
    assert plugin.get_account_url() == "https://sso.example.org/realms/computor/account/"


def test_an_uninitialised_plugin_names_none(plugin):
    assert plugin.get_account_url() is None


@pytest.mark.asyncio
async def test_providers_carry_the_account_console(plugin, monkeypatch):
    monkeypatch.setenv("KEYCLOAK_PUBLIC_URL", "https://computor.at/auth")
    registry = SimpleNamespace(
        get_enabled_plugins=lambda: ["keycloak"],
        get_plugin_metadata=lambda _name: plugin.metadata,
        get_plugin=lambda _name: plugin,
    )
    monkeypatch.setattr(auth_api, "get_plugin_registry", lambda: registry)

    [provider] = await auth_api.list_providers()
    assert provider.login_url == "/auth/keycloak/login"
    assert provider.account_url == "https://computor.at/auth/realms/computor/account/"
