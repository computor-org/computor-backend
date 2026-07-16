#!/usr/bin/env python3
"""
Idempotently register external OIDC identity providers in Keycloak (brokering).

Each provider is *brokered* by Keycloak: users log in through Keycloak, which
delegates to the external IdP, then issues its own tokens to computor-backend. So
the backend and all downstream services (Forgejo, GitLab, Coder) keep talking only
to Keycloak, with email as the cross-system join key.

Providers are defined in a JSON file (default: /idp/identity-providers.json) that
is operator-managed and NOT committed — see data/keycloak/identity-providers.example.json
for the schema. Secrets are NOT in that file: each entry names an env var via
"clientSecretEnv" and the value is read from the environment here, so a client
secret only ever lives in .env -> container env -> Keycloak, never on disk in a
config file.

Safe to run on every boot: each provider and its attribute mappers is created if
absent and updated in place if present. A missing or empty providers file is a
no-op (exit 0) — brokered IdPs are optional.

Stdlib only (urllib + json) so it runs unchanged in a slim python image (the
one-shot compose service) and on a host (manual run), with no pip install.

Env:
  KEYCLOAK_SERVER_URL_INTERNAL  Keycloak base URL (falls back to KEYCLOAK_SERVER_URL)
  KEYCLOAK_REALM                target realm (default: computor)
  KEYCLOAK_ADMIN /
  KEYCLOAK_ADMIN_PASSWORD       master-realm admin credentials
  IDENTITY_PROVIDERS_FILE       providers JSON path (default: /idp/identity-providers.json)
  IDP_<NAME>_CLIENT_SECRET      one per provider, named by its "clientSecretEnv"
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Optional: load a local .env when run manually on a host. In the one-shot
# container the vars already come from the environment, so this is best-effort.
try:
    from dotenv import load_dotenv  # type: ignore

    _env = Path(__file__).resolve().parents[1] / ".env"
    if _env.exists():
        load_dotenv(_env)
except Exception:
    pass


def _log(msg: str) -> None:
    print(f"[idp-setup] {msg}", flush=True)


def _request(method, url, token=None, json_body=None, form_body=None):
    """Make an HTTP request, returning (status_code, parsed_body).

    Never raises on HTTP error status — returns the code and body so callers can
    branch (e.g. 404 -> create). Raises only on transport-level failures.
    """
    headers = {}
    data = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if json_body is not None:
        data = json.dumps(json_body).encode()
        headers["Content-Type"] = "application/json"
    elif form_body is not None:
        data = urllib.parse.urlencode(form_body).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return resp.status, _parse(raw)
    except urllib.error.HTTPError as e:
        return e.code, _parse(e.read())


def _parse(raw):
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return raw.decode("utf-8", "replace")


def get_admin_token(base, realm_user, realm_pass):
    url = f"{base}/realms/master/protocol/openid-connect/token"
    status, body = _request(
        "POST",
        url,
        form_body={
            "grant_type": "password",
            "username": realm_user,
            "password": realm_pass,
            "client_id": "admin-cli",
        },
    )
    if status != 200 or not isinstance(body, dict):
        raise SystemExit(f"Keycloak admin auth failed: {status} {body}")
    return body["access_token"]


def import_oidc_config(base, realm, token, discovery_url):
    """Expand a discovery URL into Keycloak's OIDC config (the UI's 'import from URL')."""
    url = f"{base}/admin/realms/{realm}/identity-provider/import-config"
    status, body = _request(
        "POST", url, token=token,
        json_body={"fromUrl": discovery_url, "providerId": "oidc"},
    )
    if status != 200 or not isinstance(body, dict):
        raise RuntimeError(f"discovery import failed for {discovery_url}: {status} {body}")
    return body


def upsert_provider(base, realm, token, entry):
    alias = entry["alias"]
    secret_env = entry["clientSecretEnv"]
    secret = os.environ.get(secret_env)
    if not secret:
        raise RuntimeError(
            f"provider '{alias}': env var {secret_env} is empty/unset "
            f"(add it to .env)"
        )

    # Build the OIDC config: discovery URL expands to endpoints; an explicit
    # "config" block (no discovery) is used verbatim. Then layer client creds on.
    if entry.get("discoveryUrl"):
        config = import_oidc_config(base, realm, token, entry["discoveryUrl"])
    else:
        config = dict(entry.get("config", {}))
    config.update(
        {
            "clientId": entry["clientId"],
            "clientSecret": secret,
            "clientAuthMethod": entry.get("clientAuthMethod", "client_secret_post"),
            "defaultScope": entry.get("defaultScopes", "openid email profile"),
            "syncMode": entry.get("syncMode", "FORCE"),
        }
    )

    representation = {
        "alias": alias,
        "displayName": entry.get("displayName", alias),
        "providerId": entry.get("providerId", "oidc"),
        "enabled": entry.get("enabled", True),
        "trustEmail": entry.get("trustEmail", True),
        "storeToken": entry.get("storeToken", False),
        "linkOnly": False,
        # The built-in flow links to an existing account by (verified) email,
        # which is what keeps email-as-join-key intact across systems.
        "firstBrokerLoginFlowAlias": entry.get(
            "firstBrokerLoginFlowAlias", "first broker login"
        ),
        "config": config,
    }

    instances = f"{base}/admin/realms/{realm}/identity-provider/instances"
    status, _ = _request("GET", f"{instances}/{alias}", token=token)
    if status == 200:
        st, body = _request("PUT", f"{instances}/{alias}", token=token, json_body=representation)
        if st not in (200, 204):
            raise RuntimeError(f"update IdP '{alias}' failed: {st} {body}")
        _log(f"updated identity provider '{alias}'")
    elif status == 404:
        st, body = _request("POST", instances, token=token, json_body=representation)
        if st not in (200, 201):
            raise RuntimeError(f"create IdP '{alias}' failed: {st} {body}")
        _log(f"created identity provider '{alias}'")
    else:
        raise RuntimeError(f"probing IdP '{alias}' failed: {status}")

    _reconcile_mappers(base, realm, token, entry)


def _reconcile_mappers(base, realm, token, entry):
    """Create/update the claim->user-attribute mappers (email, names)."""
    alias = entry["alias"]
    claim_map = entry.get(
        "mappers", {"email": "email", "givenName": "given_name", "familyName": "family_name"}
    )
    # (mapper name suffix, target Keycloak user attribute, source claim key)
    wanted = [
        ("email", "email", claim_map.get("email", "email")),
        ("firstName", "firstName", claim_map.get("givenName", "given_name")),
        ("lastName", "lastName", claim_map.get("familyName", "family_name")),
    ]

    mappers_url = f"{base}/admin/realms/{realm}/identity-provider/instances/{alias}/mappers"
    status, existing = _request("GET", mappers_url, token=token)
    by_name = {m["name"]: m for m in existing} if (status == 200 and isinstance(existing, list)) else {}

    for suffix, user_attr, claim in wanted:
        name = f"{alias}-{suffix}"
        representation = {
            "name": name,
            "identityProviderAlias": alias,
            "identityProviderMapper": "oidc-user-attribute-idp-mapper",
            "config": {
                "syncMode": "INHERIT",
                "claim": claim,
                "user.attribute": user_attr,
            },
        }
        if name in by_name:
            mid = by_name[name]["id"]
            representation["id"] = mid
            st, body = _request("PUT", f"{mappers_url}/{mid}", token=token, json_body=representation)
            if st not in (200, 204):
                raise RuntimeError(f"update mapper '{name}' failed: {st} {body}")
        else:
            st, body = _request("POST", mappers_url, token=token, json_body=representation)
            if st not in (200, 201):
                raise RuntimeError(f"create mapper '{name}' failed: {st} {body}")


def main():
    base = (
        os.environ.get("KEYCLOAK_SERVER_URL_INTERNAL")
        or os.environ.get("KEYCLOAK_SERVER_URL")
        or "http://localhost:8180"
    ).rstrip("/")
    realm = os.environ.get("KEYCLOAK_REALM", "computor")
    admin = os.environ.get("KEYCLOAK_ADMIN")
    admin_pass = os.environ.get("KEYCLOAK_ADMIN_PASSWORD")
    providers_file = os.environ.get("IDENTITY_PROVIDERS_FILE", "/idp/identity-providers.json")

    path = Path(providers_file)
    if not path.exists():
        _log(f"no providers file at {providers_file} — nothing to configure")
        return
    try:
        providers = json.loads(path.read_text())
    except ValueError as e:
        raise SystemExit(f"{providers_file} is not valid JSON: {e}")
    if not isinstance(providers, list):
        raise SystemExit(f"{providers_file} must be a JSON array of providers")

    active = [p for p in providers if p.get("enabled", True)]
    if not active:
        _log("providers file has no enabled providers — nothing to configure")
        return

    if not admin or not admin_pass:
        raise SystemExit("KEYCLOAK_ADMIN / KEYCLOAK_ADMIN_PASSWORD must be set")

    _log(f"configuring {len(active)} identity provider(s) on realm '{realm}' at {base}")
    token = get_admin_token(base, admin, admin_pass)

    failures = []
    for entry in active:
        alias = entry.get("alias", "<no-alias>")
        try:
            upsert_provider(base, realm, token, entry)
        except Exception as e:  # keep going; report all failures at the end
            _log(f"ERROR configuring '{alias}': {e}")
            failures.append(alias)

    if failures:
        raise SystemExit(f"failed to configure: {', '.join(failures)}")
    _log("identity providers configured")


if __name__ == "__main__":
    main()
