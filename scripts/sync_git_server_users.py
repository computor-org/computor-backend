#!/usr/bin/env python3
"""
Git Server User Sync

Provisions all computor users onto the system git server (GIT_SERVER) and
creates the corresponding Account rows. Safe to run multiple times — users
who already have an Account row are skipped.

Usage:
    python sync_git_server_users.py
    python sync_git_server_users.py --dry-run
    python sync_git_server_users.py --user theta

Reads GIT_SERVER_URL / GIT_SERVER_ADMIN_USERNAME / GIT_SERVER_ADMIN_PASSWORD
from the .env file in the repo root (or from the environment).
"""

import argparse
import secrets
import string
import sys
from pathlib import Path

# Resolve repo root and load .env
_repo_root = Path(__file__).resolve().parents[1]
_env_file = _repo_root / ".env"

try:
    from dotenv import load_dotenv
    if _env_file.exists():
        load_dotenv(_env_file)
except ImportError:
    pass  # dotenv optional; env vars may already be set

sys.path.insert(0, str(_repo_root / "computor-backend" / "src"))

import os
import httpx
from sqlalchemy import text


def _generate_password() -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(24))


def _get_db_session():
    from computor_backend.database import get_db_session
    return get_db_session().__enter__()


def sync_users(dry_run: bool = False, only_username: str | None = None):
    git_server = os.environ.get("GIT_SERVER", "").strip()
    git_server_url = os.environ.get("GIT_SERVER_URL", "").strip()
    admin_user = os.environ.get("GIT_SERVER_ADMIN_USERNAME", "").strip()
    admin_pass = os.environ.get("GIT_SERVER_ADMIN_PASSWORD", "").strip()

    if not git_server or not git_server_url:
        print("ERROR: GIT_SERVER and GIT_SERVER_URL must be set")
        sys.exit(1)
    if not admin_user or not admin_pass:
        print("ERROR: GIT_SERVER_ADMIN_USERNAME and GIT_SERVER_ADMIN_PASSWORD must be set")
        sys.exit(1)

    provider_type = git_server.lower()

    print(f"Git server : {git_server_url}  (type={provider_type})")
    if dry_run:
        print("DRY RUN — no changes will be made")
    print()

    db = _get_db_session()

    # Users that already have an account on this git server
    existing = {
        str(row[0])
        for row in db.execute(
            text("SELECT user_id FROM account WHERE provider = :p AND type = :t"),
            {"p": git_server_url, "t": provider_type},
        )
    }

    # All (non-service) users
    query = 'SELECT id, username, email, given_name, family_name FROM "user" WHERE is_service = false'
    params: dict = {}
    if only_username:
        query += " AND username = :u"
        params["u"] = only_username
    users = list(db.execute(text(query), params))

    if not users:
        print("No users found.")
        return

    print(f"Total users: {len(users)}  |  Already provisioned: {len(existing)}")
    to_provision = [u for u in users if str(u[0]) not in existing]
    print(f"To provision: {len(to_provision)}")
    print()

    if not to_provision:
        print("Nothing to do.")
        return

    stats = {"created": 0, "already_exists": 0, "failed": 0, "skipped": 0}

    with httpx.Client(base_url=git_server_url, auth=(admin_user, admin_pass), timeout=15.0) as client:
        # Probe connectivity
        try:
            probe = client.get("/api/v1/version")
            if not probe.is_success:
                print(f"ERROR: Git server returned {probe.status_code} — aborting")
                sys.exit(1)
            version = probe.json().get("version", "?")
            print(f"Connected to git server  version={version}\n")
        except Exception as e:
            print(f"ERROR: Cannot reach git server: {e}")
            sys.exit(1)

        for user_id, username, email, given_name, family_name in to_provision:
            user_id = str(user_id)
            display_name = (f"{given_name or ''} {family_name or ''}".strip()) or username
            safe_email = email or f"{username}@noreply.local"

            if dry_run:
                print(f"  [dry-run] would provision  {username} <{safe_email}>")
                stats["skipped"] += 1
                continue

            # Try to create; fall back to fetching if already exists on the server
            git_user_data = None
            resp = client.post(
                "/api/v1/admin/users",
                json={
                    "source_id": 0,
                    "login_name": username,
                    "username": username,
                    "email": safe_email,
                    "full_name": display_name,
                    "password": _generate_password(),
                    "must_change_password": False,
                    "send_notify": False,
                    "visibility": "private",
                },
            )
            if resp.status_code == 422:
                r2 = client.get(f"/api/v1/users/{username}")
                if r2.is_success:
                    git_user_data = r2.json()
                    stats["already_exists"] += 1
                    print(f"  already exists  {username}")
                else:
                    print(f"  FAILED (exists on server, fetch failed {r2.status_code})  {username}")
                    stats["failed"] += 1
                    continue
            elif resp.is_success:
                git_user_data = resp.json()
                stats["created"] += 1
                print(f"  created  {username}")
            else:
                print(f"  FAILED ({resp.status_code})  {username}: {resp.text[:120]}")
                stats["failed"] += 1
                continue

            if not git_user_data:
                continue

            git_username = git_user_data.get("login", username)
            git_user_id = git_user_data.get("id")
            try:
                db.execute(
                    text(
                        """
                        INSERT INTO account (provider, type, provider_account_id, user_id, properties)
                        VALUES (:provider, :type, :account_id, :user_id, :props::jsonb)
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    {
                        "provider": git_server_url,
                        "type": provider_type,
                        "account_id": git_username,
                        "user_id": user_id,
                        "props": f'{{"git_user_id": {git_user_id}}}',
                    },
                )
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"  FAILED (DB insert)  {username}: {e}")
                stats["failed"] += 1

    print()
    print("=" * 40)
    if dry_run:
        print(f"Would provision: {stats['skipped']}")
    else:
        print(f"Created        : {stats['created']}")
        print(f"Already existed: {stats['already_exists']}")
        print(f"Failed         : {stats['failed']}")


def main():
    parser = argparse.ArgumentParser(description="Sync computor users to the system git server")
    parser.add_argument("--dry-run", action="store_true", help="Print what would happen without making changes")
    parser.add_argument("--user", metavar="USERNAME", help="Sync a single user instead of all")
    args = parser.parse_args()
    sync_users(dry_run=args.dry_run, only_username=args.user)


if __name__ == "__main__":
    main()
