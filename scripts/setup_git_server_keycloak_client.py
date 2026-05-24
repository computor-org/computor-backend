#!/usr/bin/env python3
"""
Setup Keycloak OIDC client for the system git server (Forgejo or GitLab).

Creates a confidential OIDC client in Keycloak that Forgejo/GitLab use for SSO.
Safe to run multiple times — if the client already exists the existing secret is printed.

Usage:
    python scripts/setup_git_server_keycloak_client.py
    python scripts/setup_git_server_keycloak_client.py --dry-run

Required env vars: KEYCLOAK_SERVER_URL, KEYCLOAK_REALM,
                   KEYCLOAK_ADMIN, KEYCLOAK_ADMIN_PASSWORD,
                   GIT_SERVER, GIT_SERVER_URL

Optional env vars:
    GIT_SERVER_KEYCLOAK_CLIENT_ID      default: value of GIT_SERVER (e.g. "forgejo")
    GIT_SERVER_KEYCLOAK_CLIENT_SECRET  if set, used as the client secret instead of generating one
"""

import argparse
import secrets
import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[1]
_env_file = _repo_root / ".env"

try:
    from dotenv import load_dotenv
    if _env_file.exists():
        load_dotenv(_env_file)
except ImportError:
    pass

import os
import httpx


def _get_admin_token(server_url: str, admin_user: str, admin_pass: str) -> str:
    resp = httpx.post(
        f"{server_url}/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "username": admin_user,
            "password": admin_pass,
            "client_id": "admin-cli",
        },
        timeout=15.0,
    )
    if not resp.is_success:
        print(f"ERROR: Keycloak admin auth failed: {resp.status_code} {resp.text[:200]}")
        sys.exit(1)
    return resp.json()["access_token"]


def _find_client(hc: httpx.Client, realm: str, client_id: str) -> dict | None:
    resp = hc.get(f"/admin/realms/{realm}/clients", params={"clientId": client_id, "search": "false"})
    if not resp.is_success:
        return None
    results = resp.json()
    return results[0] if results else None


def _get_client_secret(hc: httpx.Client, realm: str, internal_id: str) -> str:
    resp = hc.get(f"/admin/realms/{realm}/clients/{internal_id}/client-secret")
    return resp.json().get("value", "") if resp.is_success else ""


def setup_client(dry_run: bool = False) -> None:
    server_url = os.environ.get("KEYCLOAK_SERVER_URL", "").strip()
    realm      = os.environ.get("KEYCLOAK_REALM", "").strip()
    admin_user = os.environ.get("KEYCLOAK_ADMIN", "").strip()
    admin_pass = os.environ.get("KEYCLOAK_ADMIN_PASSWORD", "").strip()
    git_server     = os.environ.get("GIT_SERVER", "").strip()
    git_server_url = os.environ.get("GIT_SERVER_URL", "").strip()
    client_id      = os.environ.get("GIT_SERVER_KEYCLOAK_CLIENT_ID", git_server).strip()
    preset_secret  = os.environ.get("GIT_SERVER_KEYCLOAK_CLIENT_SECRET", "").strip()

    if not all([server_url, realm, admin_user, admin_pass]):
        print("ERROR: KEYCLOAK_SERVER_URL, KEYCLOAK_REALM, KEYCLOAK_ADMIN, KEYCLOAK_ADMIN_PASSWORD must be set")
        sys.exit(1)
    if not git_server or not git_server_url:
        print("ERROR: GIT_SERVER and GIT_SERVER_URL must be set")
        sys.exit(1)

    provider = git_server.lower()
    if provider == "forgejo":
        redirect_uris = [f"{git_server_url.rstrip('/')}/user/oauth2/Keycloak/callback"]
    elif provider == "gitlab":
        redirect_uris = [f"{git_server_url.rstrip('/')}/users/auth/openid_connect/callback"]
    else:
        print(f"ERROR: Unknown GIT_SERVER '{git_server}' — expected 'forgejo' or 'gitlab'")
        sys.exit(1)

    print(f"Keycloak  : {server_url}  realm={realm}")
    print(f"Git server: {git_server_url}  type={provider}")
    print(f"Client ID : {client_id}")
    print(f"Redirect  : {redirect_uris[0]}")
    if dry_run:
        print("DRY RUN — no changes will be made")
    print()

    token = _get_admin_token(server_url, admin_user, admin_pass)

    with httpx.Client(
        base_url=server_url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=15.0,
    ) as hc:
        existing = _find_client(hc, realm, client_id)

        if existing:
            internal_id = existing["id"]
            secret = _get_client_secret(hc, realm, internal_id)
            print(f"Client '{client_id}' already exists (id={internal_id})")
            _print_result(provider, realm, client_id, secret, server_url, git_server_url)
            return

        if dry_run:
            print(f"[dry-run] would create client '{client_id}'  redirectUris={redirect_uris}")
            return

        client_secret = preset_secret or secrets.token_urlsafe(32)
        payload = {
            "clientId": client_id,
            "name": f"computor {provider} OIDC",
            "enabled": True,
            "protocol": "openid-connect",
            "publicClient": False,
            "clientAuthenticatorType": "client-secret",
            "secret": client_secret,
            "redirectUris": redirect_uris,
            "webOrigins": ["+"],
            "standardFlowEnabled": True,
            "directAccessGrantsEnabled": False,
            "serviceAccountsEnabled": False,
            "attributes": {
                "post.logout.redirect.uris": "+",
                # PKCE is intentionally NOT enforced for Forgejo/GitLab:
                # neither sends a code_challenge in its OIDC flow, and enforcing
                # S256 makes Keycloak reject the authorization request with
                # "Missing parameter: code_challenge_method".
            },
        }

        resp = hc.post(f"/admin/realms/{realm}/clients", json=payload)
        if resp.status_code == 409:
            print(f"Client '{client_id}' created concurrently — re-run to fetch secret")
            sys.exit(1)
        if not resp.is_success:
            print(f"ERROR: {resp.status_code} {resp.text[:300]}")
            sys.exit(1)

        # Fetch actual secret from Keycloak (may differ from what we sent)
        created = _find_client(hc, realm, client_id)
        actual_secret = client_secret
        if created:
            fetched = _get_client_secret(hc, realm, created["id"])
            if fetched:
                actual_secret = fetched

        print(f"Created client '{client_id}'")
        _print_result(provider, realm, client_id, actual_secret, server_url, git_server_url)


def _print_result(
    provider: str,
    realm: str,
    client_id: str,
    secret: str,
    server_url: str,
    git_server_url: str,
) -> None:
    print(f"\nClient secret: {secret}")
    if provider == "forgejo":
        print(f"\n# Add to computor-git/forgejo/.env:")
        print(f"KEYCLOAK_URL={server_url}")
        print(f"KEYCLOAK_REALM={realm}")
        print(f"FORGEJO_KEYCLOAK_CLIENT_ID={client_id}")
        print(f"FORGEJO_KEYCLOAK_CLIENT_SECRET={secret}")
        print(f"\nThen restart Forgejo: ./stop.sh && ./start.sh")
    elif provider == "gitlab":
        print(f"\n# Add to computor-git/gitlab/.env:")
        print(f"KEYCLOAK_URL={server_url}")
        print(f"KEYCLOAK_REALM={realm}")
        print(f"GITLAB_KEYCLOAK_CLIENT_ID={client_id}")
        print(f"GITLAB_KEYCLOAK_CLIENT_SECRET={secret}")
        print(f"\nThen restart GitLab: ./stop.sh && ./start.sh")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create Keycloak OIDC client for the system git server")
    parser.add_argument("--dry-run", action="store_true", help="Print what would happen without making changes")
    args = parser.parse_args()
    setup_client(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
