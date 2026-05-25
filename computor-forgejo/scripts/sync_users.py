#!/usr/bin/env python3
"""
Git Server User Sync

Ensures every computor user has an Account row linking them to the system git
server (GIT_SERVER). Safe to run multiple times — users who already have a row
are skipped.

With OIDC configured, the actual Forgejo/GitLab account is created on the
user's first login. This script just pre-populates the Account table so the
relationship is tracked from the start.

Usage:
    python sync_git_server_users.py
    python sync_git_server_users.py --dry-run
    python sync_git_server_users.py --user theta

Reads GIT_SERVER_URL / GIT_SERVER from the .env file in the repo root
(or from the environment).
"""

import argparse
import re
import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[2]
_env_file = _repo_root / ".env"

try:
    from dotenv import load_dotenv
    if _env_file.exists():
        load_dotenv(_env_file)
except ImportError:
    pass

sys.path.insert(0, str(_repo_root / "computor-backend" / "src"))

import json
import os
from sqlalchemy import text


def _get_db_session():
    from computor_backend.database import get_db_session
    return get_db_session().__enter__()


def _username_from_email(email: str) -> str:
    """Derive a valid git server username from an email address."""
    local = email.split("@")[0]
    username = re.sub(r"[^a-zA-Z0-9._-]", "-", local)
    username = re.sub(r"-{2,}", "-", username).strip("-")
    return username or "user"


def sync_users(dry_run: bool = False, only_email: str | None = None):
    git_server = os.environ.get("GIT_SERVER", "").strip()
    git_server_url = os.environ.get("GIT_SERVER_URL", "").strip()

    if not git_server or not git_server_url:
        print("ERROR: GIT_SERVER and GIT_SERVER_URL must be set")
        sys.exit(1)

    provider_type = git_server.lower()

    print(f"Git server : {git_server_url}  (type={provider_type})")
    if dry_run:
        print("DRY RUN — no changes will be made")
    print()

    db = _get_db_session()

    existing = {
        str(row[0])
        for row in db.execute(
            text("SELECT user_id FROM account WHERE provider = :p AND type = :t"),
            {"p": git_server_url, "t": provider_type},
        )
    }

    query = 'SELECT id, email FROM "user" WHERE is_service = false'
    params: dict = {}
    if only_email:
        query += " AND email = :e"
        params["e"] = only_email
    users = list(db.execute(text(query), params))

    if not users:
        print("No users found.")
        return

    to_provision = [u for u in users if str(u[0]) not in existing]
    print(f"Total users: {len(users)}  |  Already linked: {len(existing)}")
    print(f"To link    : {len(to_provision)}")
    print()

    if not to_provision:
        print("Nothing to do.")
        return

    inserted = skipped = failed = 0

    for user_id, email in to_provision:
        user_id = str(user_id)
        git_username = _username_from_email(email or user_id)

        if dry_run:
            print(f"  [dry-run] would link  {email}  (git: {git_username})")
            skipped += 1
            continue

        try:
            db.execute(
                text(
                    """
                    INSERT INTO account (provider, type, provider_account_id, user_id, properties)
                    VALUES (:provider, :type, :account_id, :user_id, CAST(:props AS jsonb))
                    ON CONFLICT DO NOTHING
                    """
                ),
                {
                    "provider": git_server_url,
                    "type": provider_type,
                    "account_id": git_username,
                    "user_id": user_id,
                    "props": json.dumps({}),
                },
            )
            db.commit()
            print(f"  linked  {email}  (git: {git_username})")
            inserted += 1
        except Exception as e:
            db.rollback()
            print(f"  FAILED  {email}: {e}")
            failed += 1

    print()
    print("=" * 40)
    if dry_run:
        print(f"Would link: {skipped}")
    else:
        print(f"Linked : {inserted}")
        print(f"Failed : {failed}")


def main():
    parser = argparse.ArgumentParser(
        description="Link computor users to the system git server in the Account table"
    )
    parser.add_argument("--dry-run", action="store_true", help="Print what would happen without making changes")
    parser.add_argument("--user", metavar="EMAIL", help="Link a single user by email instead of all")
    args = parser.parse_args()
    sync_users(dry_run=args.dry_run, only_email=args.user)


if __name__ == "__main__":
    main()
