"""Behavioral tests for brokered social-provider registration."""

from types import SimpleNamespace

import pytest

from computor_backend.api import auth
from computor_backend.auth import social
from computor_backend import redis_cache
from computor_backend.exceptions import BadRequestException
from computor_backend.plugins.base import AuthenticationType, PluginMetadata


def test_social_provider_allowlist_and_keycloak_hint(monkeypatch):
    monkeypatch.setenv("COMPUTOR_SOCIAL_LOGIN_PROVIDERS", "gitlab,google")
    monkeypatch.setenv("KEYCLOAK_IDP_GOOGLE_ALIAS", "google-prod")

    providers = social.enabled_social_providers()
    assert [provider["name"] for provider in providers] == ["google", "gitlab"]
    assert providers[0]["alias"] == "google-prod"
    assert social.add_keycloak_identity_provider_hint(
        "https://idp.example/authorize?client_id=computor", "google-prod"
    ).endswith("client_id=computor&kc_idp_hint=google-prod")


def test_student_registration_cannot_bootstrap_admin_from_upstream_groups():
    assert social.should_bootstrap_admin(
        groups=["/administrators"], registration=True
    ) is False
    assert social.should_bootstrap_admin(
        groups=["/administrators"], registration=False
    ) is True


@pytest.mark.asyncio
async def test_provider_listing_exposes_only_configured_social_buttons(monkeypatch):
    metadata = PluginMetadata(
        name="keycloak",
        version="1",
        description="test",
        provider_name="Keycloak",
        provider_type=AuthenticationType.OIDC,
    )

    class Registry:
        def get_enabled_plugins(self):
            return ["keycloak"]

        def get_plugin_metadata(self, name):
            return metadata

    monkeypatch.setattr(auth, "get_plugin_registry", lambda: Registry())
    monkeypatch.setenv("COMPUTOR_SOCIAL_LOGIN_PROVIDERS", "google,gitlab")

    providers = await auth.list_providers()
    assert [provider.name for provider in providers] == ["keycloak", "google", "gitlab"]
    assert providers[1].login_url.endswith("provider_hint=google")


@pytest.mark.asyncio
async def test_social_login_redirect_contains_hint_and_student_registration_state(monkeypatch):
    stored = {}

    class Redis:
        async def set(self, key, value, ex):
            stored[key] = (value, ex)

    class Registry:
        def get_enabled_plugins(self):
            return ["keycloak"]

        def get_plugin(self, name):
            return object()

        def get_login_url(self, provider, redirect_uri, state):
            return "https://idp.example/authorize?state=" + state

    monkeypatch.setattr(auth, "get_plugin_registry", lambda: Registry())
    async def fake_get_redis_client():
        return Redis()

    monkeypatch.setattr(redis_cache, "get_redis_client", fake_get_redis_client)
    monkeypatch.setenv("COMPUTOR_SOCIAL_LOGIN_PROVIDERS", "google")
    monkeypatch.setenv("NEXT_PUBLIC_API_URL", "https://api.example")

    request = SimpleNamespace(
        headers={},
        url_for=lambda name, **kwargs: "http://localhost/unused",
    )
    response = await auth.initiate_login(
        provider="keycloak",
        redirect_uri="https://app.example/auth/success",
        provider_hint="google",
        registration=True,
        request=request,
    )

    assert "kc_idp_hint=google" in response.headers["location"]
    state_key, (raw_state, ttl) = next(iter(stored.items()))
    assert state_key.startswith("sso_state:")
    assert ttl == 1800
    assert '"social_provider": "google"' in raw_state
    assert '"registration": true' in raw_state


@pytest.mark.asyncio
async def test_registration_requires_a_configured_social_provider(monkeypatch):
    class Registry:
        def get_enabled_plugins(self):
            return ["keycloak"]

    monkeypatch.setattr(auth, "get_plugin_registry", lambda: Registry())

    with pytest.raises(BadRequestException, match="configured social provider"):
        await auth.initiate_login(
            provider="keycloak",
            provider_hint=None,
            registration=True,
            request=SimpleNamespace(headers={}, url_for=lambda name, **kwargs: "http://localhost"),
        )
