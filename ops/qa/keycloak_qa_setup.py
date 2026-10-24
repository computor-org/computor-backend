#!/usr/bin/env python3
"""Reconcile the QA realm's signup policy the way computor.at has it.

Runs after Keycloak is healthy, in a throwaway python container on the stack
network (qactl.sh up). It reuses the repository's own reconcilers instead of
copying them:

1. setup_identity_providers.ensure_realm_settings / ensure_account_console_scopes
   (what keycloak-idp-setup does on every production boot);
2. setup_abuse.configure: the ALTCHA proof-of-work and honeypot registration
   flow that computor.at serves (needs the provider JAR in /opt/keycloak/providers);
3. VERIFY_EMAIL before UPDATE_PASSWORD, both enabled: Keycloak 26 then asks for
   the password only after the verification link (issues#441);
4. setup_terms.py with COMPUTOR_LEGAL_PROFILE=computor-at (Terms of Use 1.2);
5. a read-back of the same policy that computor-infra's verify-registration.py
   checks on production, so a drift fails the QA start instead of a test.

Env: KEYCLOAK_SERVER_URL_INTERNAL, KEYCLOAK_REALM, KEYCLOAK_ADMIN,
KEYCLOAK_ADMIN_PASSWORD, KEYCLOAK_ABUSE_SECRET, KEYCLOAK_CLIENT_ID.
"""

from __future__ import annotations

import os
import subprocess
import sys
import urllib.parse

sys.path.insert(0, os.environ.get("KEYCLOAK_SCRIPTS_DIR", "/kc"))

from setup_identity_providers import (  # noqa: E402
    _request,
    ensure_account_console_scopes,
    ensure_realm_settings,
    get_admin_token,
)
from setup_abuse import configure as configure_abuse  # noqa: E402

ACTION_ORDER = {"TERMS_AND_CONDITIONS": 10, "VERIFY_EMAIL": 20, "UPDATE_PASSWORD": 30}


def _admin(base: str, realm: str) -> str:
    return f"{base}/admin/realms/{urllib.parse.quote(realm, safe='')}"


def ensure_action_order(base: str, realm: str, token: str) -> None:
    """VERIFY_EMAIL and UPDATE_PASSWORD enabled, verification first.

    TERMS_AND_CONDITIONS is left to setup_terms.py (it is enabled only after
    its texts are verified); only its priority is placed here when present.
    """
    url = _admin(base, realm) + "/authentication/required-actions"
    status, actions = _request("GET", url, token=token)
    if status != 200:
        raise RuntimeError(f"reading required actions failed: {status}")
    for action in actions:
        alias = action.get("alias")
        if alias not in ACTION_ORDER:
            continue
        wanted = dict(action, priority=ACTION_ORDER[alias])
        if alias != "TERMS_AND_CONDITIONS":
            wanted["enabled"] = True
        if wanted != action:
            st, body = _request("PUT", f"{url}/{urllib.parse.quote(alias)}", token=token,
                                json_body=wanted)
            if st not in (200, 204):
                raise RuntimeError(f"updating required action {alias} failed: {st} {body}")
            print(f"[qa-keycloak] required action {alias}: priority {ACTION_ORDER[alias]}")


def verify_policy(base: str, realm: str, token: str) -> None:
    """The checks of computor-infra prod/verify-registration.py, read only."""
    root = _admin(base, realm)
    status, settings = _request("GET", root, token=token)
    if status != 200:
        raise RuntimeError(f"reading realm failed: {status}")
    for key in ("enabled", "registrationAllowed", "verifyEmail", "resetPasswordAllowed"):
        if settings.get(key) is not True:
            raise RuntimeError(f"realm setting not enabled: {key}")
    if (settings.get("smtpServer") or {}).get("host") != "mailpit":
        raise RuntimeError("realm SMTP is not the stack's Mailpit")
    flow = settings.get("registrationFlow")
    _, executions = _request(
        "GET", f"{root}/authentication/flows/{urllib.parse.quote(flow, safe='')}/executions",
        token=token)
    passwords = [e for e in executions if e.get("providerId") == "registration-password-action"]
    if len(passwords) != 1 or passwords[0].get("requirement") != "REQUIRED":
        raise RuntimeError("registration flow needs exactly one REQUIRED Password Validation")
    if not any(e.get("providerId") == "computor-registration-abuse"
               and e.get("requirement") == "REQUIRED" for e in executions):
        raise RuntimeError("registration flow lacks the signup protection step")
    _, actions = _request("GET", f"{root}/authentication/required-actions", token=token)
    by_alias = {a["alias"]: a for a in actions}
    for alias in ("VERIFY_EMAIL", "UPDATE_PASSWORD", "TERMS_AND_CONDITIONS"):
        if not by_alias.get(alias, {}).get("enabled"):
            raise RuntimeError(f"required action disabled: {alias}")
    if by_alias["VERIFY_EMAIL"]["priority"] >= by_alias["UPDATE_PASSWORD"]["priority"]:
        raise RuntimeError("email verification must precede password setup")
    print(f"[qa-keycloak] policy verified: flow={flow}, email first, terms, signup protection")


def main() -> int:
    base = os.environ["KEYCLOAK_SERVER_URL_INTERNAL"].rstrip("/")
    realm = os.environ.get("KEYCLOAK_REALM", "computor")
    token = get_admin_token(base, os.environ["KEYCLOAK_ADMIN"],
                            os.environ["KEYCLOAK_ADMIN_PASSWORD"])
    ensure_realm_settings(base, realm, token)
    ensure_account_console_scopes(base, realm, token)
    configure_abuse(base, realm, token, os.environ["KEYCLOAK_ABUSE_SECRET"],
                    cost=int(os.environ.get("KEYCLOAK_ABUSE_COST", "10000")),
                    ttl=int(os.environ.get("KEYCLOAK_ABUSE_TTL", "300")))
    print("[qa-keycloak] signup protection reconciled")
    ensure_action_order(base, realm, token)
    env = dict(os.environ, COMPUTOR_LEGAL_PROFILE="computor-at")
    scripts = os.environ.get("KEYCLOAK_SCRIPTS_DIR", "/kc")
    subprocess.run([sys.executable, f"{scripts}/setup_terms.py"], env=env, check=True)
    # setup_terms appends TERMS_AND_CONDITIONS with its own priority; place it.
    ensure_action_order(base, realm, token)
    verify_policy(base, realm, token)
    return 0


if __name__ == "__main__":
    sys.exit(main())
