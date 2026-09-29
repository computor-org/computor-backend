#!/usr/bin/env python3
"""
Idempotently require acceptance of the computor.at Terms of Use in Keycloak.

FOR computor.at ONLY. Do NOT run this against code.tugraz.at (TU Graz internal
deployment of the same code): that instance is covered by TU Graz's own terms
and must not show computor.at's public texts. The script refuses to run unless
COMPUTOR_LEGAL_PROFILE=computor-at is set, as a guard against running it on
the wrong deployment by accident.

What it reconciles on realm KEYCLOAK_REALM (default: computor), in this order:
  1. Internationalization enabled with "de" and "en" in supportedLocales
     (existing locales and defaultLocale are kept).
  2. Realm localization overrides termsTitle / termsText / doAccept / doDecline
     for de and en, read from computor-at-terms.json next to this script.
  3. Verification: every one of those values is read back and must match.
  4. Only then: required action "Terms and Conditions" (alias
     TERMS_AND_CONDITIONS; older Keycloak: terms_and_conditions) registered,
     enabled and a *default* action, so every newly created account (incl.
     GitHub first broker login) must accept before a token is issued.
Any failure in 1-3 aborts before step 4, so users can never be asked to
accept Keycloak's placeholder terms text.

Existing accounts are not gated by a default action. This script deliberately
does not touch users: replacing a user's requiredActions from a snapshot can
drop an action (e.g. UPDATE_PASSWORD) added concurrently. See ops/README.md for
the one-off maintenance procedure.

Each step reads first and writes only on a difference, so a second run changes
nothing. --dry-run prints what would change without writing.

Stdlib only; reuses the HTTP helpers of setup_identity_providers.py.

Env:
  COMPUTOR_LEGAL_PROFILE        must be "computor-at" (safety guard)
  KEYCLOAK_SERVER_URL_INTERNAL  Keycloak base URL (falls back to KEYCLOAK_SERVER_URL)
  KEYCLOAK_REALM                target realm (default: computor)
  KEYCLOAK_ADMIN /
  KEYCLOAK_ADMIN_PASSWORD       master-realm admin credentials
"""

import argparse
import json
import os
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from setup_identity_providers import _request, get_admin_token  # noqa: E402

TEXTS_FILE = Path(__file__).resolve().parent / "computor-at-terms.json"
TERMS_ALIASES = ("TERMS_AND_CONDITIONS", "terms_and_conditions")
LOCALES = ("de", "en")


def _log(msg: str) -> None:
    print(f"[terms-setup] {msg}", flush=True)


class Keycloak:
    def __init__(self, base, realm, token, dry_run):
        self.admin = f"{base}/admin/realms/{realm}"
        self.realm = realm
        self.token = token
        self.dry_run = dry_run
        self.changes = 0

    def get(self, path):
        status, body = _request("GET", self.admin + path, token=self.token)
        return status, body

    def write(self, method, path, what, json_body=None, raw_text=None):
        self.changes += 1
        if self.dry_run:
            _log(f"would {what}")
            return
        if raw_text is not None:
            status, body = _raw_text_request(method, self.admin + path, self.token, raw_text)
        else:
            status, body = _request(method, self.admin + path, token=self.token, json_body=json_body)
        if status not in (200, 201, 204):
            raise SystemExit(f"{what} failed: {status} {body}")
        _log(what)


def _raw_text_request(method, url, token, text):
    """PUT a text/plain body (the localization endpoint takes the bare string)."""
    import urllib.error
    import urllib.request

    req = urllib.request.Request(
        url,
        data=text.encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "text/plain; charset=utf-8"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def ensure_terms_required_action(kc: Keycloak) -> str:
    status, actions = kc.get("/authentication/required-actions")
    if status != 200 or not isinstance(actions, list):
        raise SystemExit(f"reading required actions failed: {status} {actions}")
    current = next((a for a in actions if a.get("alias") in TERMS_ALIASES), None)
    if current is None:
        status, unregistered = kc.get("/authentication/unregistered-required-actions")
        if status != 200 or not isinstance(unregistered, list):
            raise SystemExit(f"reading unregistered required actions failed: {status}")
        provider = next((a for a in unregistered if a.get("providerId") in TERMS_ALIASES), None)
        if provider is None:
            raise SystemExit("Keycloak offers no Terms and Conditions required action")
        kc.write("POST", "/authentication/register-required-action",
                 f"register required action {provider['providerId']}",
                 json_body={"providerId": provider["providerId"], "name": provider.get("name")})
        if kc.dry_run:
            return provider["providerId"]
        status, current = kc.get(f"/authentication/required-actions/{provider['providerId']}")
        if status != 200 or not isinstance(current, dict):
            raise SystemExit(f"reading registered required action failed: {status}")
    alias = current["alias"]
    if current.get("enabled") and current.get("defaultAction"):
        _log(f"required action {alias}: already enabled and default")
        return alias
    wanted = dict(current, enabled=True, defaultAction=True)
    kc.write("PUT", f"/authentication/required-actions/{urllib.parse.quote(alias)}",
             f"required action {alias}: enabled=true defaultAction=true", json_body=wanted)
    return alias


def ensure_internationalization(kc: Keycloak) -> None:
    status, realm = kc.get("")
    if status != 200 or not isinstance(realm, dict):
        raise SystemExit(f"reading realm '{kc.realm}' failed: {status}")
    locales = list(realm.get("supportedLocales") or [])
    missing = [loc for loc in LOCALES if loc not in locales]
    if realm.get("internationalizationEnabled") and not missing:
        _log("internationalization: already enabled with de, en")
        return
    patch = dict(realm, internationalizationEnabled=True, supportedLocales=locales + missing)
    kc.write("PUT", "", f"internationalization enabled, supportedLocales={locales + missing}",
             json_body=patch)


def ensure_localization(kc: Keycloak, texts: dict) -> None:
    for locale in LOCALES:
        status, existing = kc.get(f"/localization/{locale}")
        existing = existing if status == 200 and isinstance(existing, dict) else {}
        for key, value in texts[locale].items():
            if existing.get(key) == value:
                continue
            kc.write("PUT", f"/localization/{locale}/{key}",
                     f"localization {locale}.{key} set", raw_text=value)
    _log("localization: de/en terms texts reconciled")


def verify_localization(kc: Keycloak, texts: dict) -> None:
    """Read every terms text back; abort (before enabling the action) on any mismatch."""
    for locale in LOCALES:
        status, stored = kc.get(f"/localization/{locale}")
        if status != 200 or not isinstance(stored, dict):
            raise SystemExit(f"verifying localization {locale} failed: {status}; "
                             "required action NOT enabled")
        wrong = [key for key, value in texts[locale].items() if stored.get(key) != value]
        if wrong:
            raise SystemExit(f"localization {locale} does not match for {wrong}; "
                             "required action NOT enabled")
    _log("localization: de/en terms texts verified")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="print changes, write nothing")
    args = parser.parse_args()

    if os.environ.get("COMPUTOR_LEGAL_PROFILE") != "computor-at":
        raise SystemExit(
            "refusing to run: set COMPUTOR_LEGAL_PROFILE=computor-at. This script is for "
            "computor.at only and must NOT be run for code.tugraz.at."
        )
    base = (
        os.environ.get("KEYCLOAK_SERVER_URL_INTERNAL")
        or os.environ.get("KEYCLOAK_SERVER_URL")
        or "http://localhost:8180"
    ).rstrip("/")
    realm = os.environ.get("KEYCLOAK_REALM", "computor")
    admin = os.environ.get("KEYCLOAK_ADMIN")
    admin_pass = os.environ.get("KEYCLOAK_ADMIN_PASSWORD")
    if not admin or not admin_pass:
        raise SystemExit("KEYCLOAK_ADMIN / KEYCLOAK_ADMIN_PASSWORD must be set")

    texts = json.loads(TEXTS_FILE.read_text(encoding="utf-8"))
    kc = Keycloak(base, realm, get_admin_token(base, admin, admin_pass), args.dry_run)
    _log(f"realm '{realm}' at {base}{' (dry run)' if args.dry_run else ''}")

    ensure_internationalization(kc)
    ensure_localization(kc, texts)
    if kc.dry_run and kc.changes:
        _log("dry run: texts not installed yet, so the required action would be enabled "
             "only after they verify")
    else:
        verify_localization(kc, texts)
    ensure_terms_required_action(kc)
    _log(f"done: {kc.changes} change(s){' planned' if args.dry_run else ''}")


if __name__ == "__main__":
    main()
