#!/usr/bin/env python3
"""
Setup Keycloak public client for the Computor VS Code extension.

Creates the `computor-vscode` public client with OAuth 2.0 Device Authorization
Grant enabled. Public clients have no secret — the VS Code extension only needs
the client_id. Safe to run multiple times; existing client is left alone.

Usage:
    python scripts/setup_vscode_keycloak_client.py
    python scripts/setup_vscode_keycloak_client.py --dry-run

Required env vars: KEYCLOAK_SERVER_URL, KEYCLOAK_REALM,
                   KEYCLOAK_ADMIN, KEYCLOAK_ADMIN_PASSWORD

Optional:
    VSCODE_KEYCLOAK_CLIENT_ID   default: "computor-vscode"
"""

import argparse
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


def setup_client(dry_run: bool = False) -> None:
    server_url = os.environ.get("KEYCLOAK_SERVER_URL", "").strip()
    realm      = os.environ.get("KEYCLOAK_REALM", "").strip()
    admin_user = os.environ.get("KEYCLOAK_ADMIN", "").strip()
    admin_pass = os.environ.get("KEYCLOAK_ADMIN_PASSWORD", "").strip()
    client_id  = os.environ.get("VSCODE_KEYCLOAK_CLIENT_ID", "computor-vscode").strip()

    if not all([server_url, realm, admin_user, admin_pass]):
        print("ERROR: KEYCLOAK_SERVER_URL, KEYCLOAK_REALM, KEYCLOAK_ADMIN, KEYCLOAK_ADMIN_PASSWORD must be set")
        sys.exit(1)

    print(f"Keycloak  : {server_url}  realm={realm}")
    print(f"Client ID : {client_id}  (public, device flow)")
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
            print(f"Client '{client_id}' already exists (id={existing['id']}) — no changes")
            return

        if dry_run:
            print(f"[dry-run] would create public client '{client_id}' with device flow enabled")
            return

        payload = {
            "clientId": client_id,
            "name": "Computor VS Code Extension",
            "description": "Public client for the Computor VS Code extension (Device Authorization Grant)",
            "enabled": True,
            "protocol": "openid-connect",
            "publicClient": True,
            "standardFlowEnabled": False,
            "implicitFlowEnabled": False,
            "directAccessGrantsEnabled": False,
            "serviceAccountsEnabled": False,
            "attributes": {
                "oauth2.device.authorization.grant.enabled": "true",
                # PKCE intentionally not enforced — device flow clients typically
                # don't send code_challenge on the initial /auth/device request,
                # and Keycloak rejects with "Missing parameter: code_challenge_method"
                # if it's required. PKCE can be added at the token-polling step by
                # the extension itself if desired.
                "use.refresh.tokens": "true",
                "display.on.consent.screen": "false",
            },
            "fullScopeAllowed": True,
            "defaultClientScopes": ["web-origins", "openid", "profile", "roles", "email"],
            "optionalClientScopes": ["address", "phone", "offline_access", "microprofile-jwt"],
        }

        resp = hc.post(f"/admin/realms/{realm}/clients", json=payload)
        if resp.status_code == 409:
            print(f"Client '{client_id}' created concurrently — re-run to verify")
            sys.exit(1)
        if not resp.is_success:
            print(f"ERROR: {resp.status_code} {resp.text[:300]}")
            sys.exit(1)

        print(f"Created public client '{client_id}'")
        print()
        print("VS Code extension should use:")
        print(f"  device endpoint: {server_url}/realms/{realm}/protocol/openid-connect/auth/device")
        print(f"  token endpoint : {server_url}/realms/{realm}/protocol/openid-connect/token")
        print(f"  client_id      : {client_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create Keycloak public client for the VS Code extension")
    parser.add_argument("--dry-run", action="store_true", help="Print what would happen without making changes")
    args = parser.parse_args()
    setup_client(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
