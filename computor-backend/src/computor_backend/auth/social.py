"""Configuration for brokered social sign-in providers.

Computor does not put provider secrets in the browser or implement separate
token exchanges for each provider. Keycloak brokers the upstream accounts and
the backend receives the normal Keycloak OIDC session. Operators enable the
providers that are actually configured in Keycloak with
``COMPUTOR_SOCIAL_LOGIN_PROVIDERS``.
"""

import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


SOCIAL_PROVIDER_NAMES = ("google", "github", "gitlab")
_DISPLAY_NAMES = {
    "google": "Google",
    "github": "GitHub",
    "gitlab": "GitLab",
}


def enabled_social_providers() -> list[dict[str, str]]:
    """Return the configured providers in stable UI order."""
    configured = {
        name.strip().lower()
        for name in os.environ.get("COMPUTOR_SOCIAL_LOGIN_PROVIDERS", "").split(",")
        if name.strip()
    }
    return [
        {
            "name": name,
            "display_name": _DISPLAY_NAMES[name],
            "alias": os.environ.get(
                f"KEYCLOAK_IDP_{name.upper()}_ALIAS", name
            ),
        }
        for name in SOCIAL_PROVIDER_NAMES
        if name in configured
    ]


def social_provider(name: str) -> dict[str, str] | None:
    """Resolve a user-facing provider name to its configured broker alias."""
    return next(
        (provider for provider in enabled_social_providers() if provider["name"] == name.lower()),
        None,
    )


def add_keycloak_identity_provider_hint(login_url: str, alias: str) -> str:
    """Add the Keycloak broker hint without disturbing existing query values."""
    parts = urlsplit(login_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["kc_idp_hint"] = alias
    return urlunsplit(parts._replace(query=urlencode(query)))


def should_bootstrap_admin(*, groups: list[str] | None, registration: bool) -> bool:
    """Only an ordinary trusted Keycloak login may bootstrap ``_admin``.

    Social self-registration must never turn upstream claims into a global
    administrator role. Existing database roles remain authoritative and are
    not revoked here.
    """
    if registration:
        return False
    return any(group.strip("/").split("/")[-1] == "administrators" for group in (groups or []))
