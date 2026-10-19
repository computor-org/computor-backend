"""Second-factor evidence for elevated authority (computor-org/issues#485).

Holders of ``_admin`` or a global manager role must sign in to Keycloak with a
one-time code. Keycloak enforces that in the browser flow
(ops/keycloak/setup_mfa.py); this module is the backend's independent check.

Evidence is the ``amr`` claim of the Keycloak ID token, emitted by the
``oidc-amr-mapper`` that setup_mfa.py puts on the backend client. Verified
against Keycloak 26.7.4 (ops/keycloak/test_mfa_live.py): the mapper lists the
``default.reference.value`` of each execution completed in the user's SSO
session and nothing for executions without one, so setup_mfa.py gives the
role-gated OTP executions the reference ``otp``. A password+OTP login yields
``["otp"]``, which survives SSO-cookie re-authentication and refresh-token
grants of that session. The login that enrols an authenticator through the
CONFIGURE_TOTP required action yields ``[]``: the user signs in once more with
the new code. ``acr`` is not used: without an ACR-to-LoA map it only says
whether the login was interactive (``1``) or by cookie (``0``).

Kept free of backend imports so ops/keycloak/test_mfa_live.py can load it on
its own and check it against tokens from a real Keycloak.
"""

import os
from collections.abc import Iterable, Mapping
from typing import Any

# ``amr`` values that prove a possession factor (RFC 8176 names).
SECOND_FACTOR_AMR = frozenset({"otp", "hwk", "swk", "mfa"})

# Global roles that carry no management authority. Every other global role
# (``_admin``, the ``_*_manager`` roles, ``_workspace_maintainer`` and any
# custom role an operator adds) counts as elevated, so a new role fails closed.
NON_ELEVATED_GLOBAL_ROLES = frozenset({"_workspace_user"})

MFA_REALM_ROLE = "computor-mfa-required"

_TRUE = ("true", "1", "yes", "on")


def admin_mfa_enforced() -> bool:
    """Whether elevated roles need second-factor evidence on SSO sessions.

    On when Keycloak is enabled and ``KEYCLOAK_ADMIN_MFA`` is true. The prod
    Keycloak overlay defaults the variable to true; dev and tests leave it off.
    """
    if os.environ.get("KEYCLOAK_ENABLED", "true").lower() not in _TRUE:
        return False
    return os.environ.get("KEYCLOAK_ADMIN_MFA", "false").lower() in _TRUE


# Bump when the meaning of the gate changes, so principals cached under the
# old rules are rebuilt (see mfa_policy_stamp).
MFA_POLICY_VERSION = 1


def mfa_policy_stamp(enforced: bool | None = None) -> str:
    """The admin-MFA policy a Principal was built under.

    ``PrincipalBuilder.build`` records it on every Principal and each reader of
    the principal cache treats a different value as a cache miss. Switching
    enforcement on or off (or bumping MFA_POLICY_VERSION) therefore re-evaluates
    every cached principal on its next use, without relying on a successful
    invalidation of the cache. Entries cached before the stamp existed carry
    none and are rebuilt too.
    """
    if enforced is None:
        enforced = admin_mfa_enforced()
    return f"v{MFA_POLICY_VERSION}:{'on' if enforced else 'off'}"


def is_elevated_global_role(role_id: str | None) -> bool:
    return bool(role_id) and role_id not in NON_ELEVATED_GLOBAL_ROLES


def elevated_roles(role_ids: Iterable[str]) -> list:
    return [role for role in role_ids if is_elevated_global_role(role)]


def amr_values(claims: Mapping[str, Any] | None) -> list:
    """The ``amr`` claim as a list of strings (a bare string is accepted)."""
    value = (claims or {}).get("amr")
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [item for item in value if isinstance(item, str)]
    return []


def has_mfa_evidence(claims: Mapping[str, Any] | None) -> bool:
    """True if the token's ``amr`` names a second factor."""
    return any(value in SECOND_FACTOR_AMR for value in amr_values(claims))
