"""backfill git server accounts for existing users

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-05-21

Provisions existing computor users onto the system git server (GIT_SERVER) if
configured, and creates Account rows linking them. Skipped silently when
GIT_SERVER is not set or the server is unreachable.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import os
import json
import re
import secrets
import string
import logging

logger = logging.getLogger(__name__)

revision: str = 'c2d3e4f5a6b7'
down_revision: Union[str, None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _generate_password() -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(24))


def _username_from_email(email: str) -> str:
    local = email.split("@")[0]
    username = re.sub(r"[^a-zA-Z0-9._-]", "-", local)
    username = re.sub(r"-{2,}", "-", username).strip("-")
    return username or "user"


def upgrade() -> None:
    git_server = os.environ.get("GIT_SERVER", "").strip()
    git_server_url = os.environ.get("GIT_SERVER_URL", "").strip()
    admin_user = os.environ.get("GIT_SERVER_ADMIN_USERNAME", "").strip()
    admin_pass = os.environ.get("GIT_SERVER_ADMIN_PASSWORD", "").strip()

    if not git_server or not git_server_url or not admin_user or not admin_pass:
        logger.info("GIT_SERVER not fully configured — skipping git account backfill")
        return

    try:
        import httpx
    except ImportError:
        logger.warning("httpx not available — skipping git account backfill")
        return

    provider_type = git_server.lower()
    bind = op.get_bind()

    # Users that already have a git server account for this provider
    existing_sql = sa.text(
        "SELECT user_id FROM account WHERE provider = :provider AND type = :type"
    )
    existing_user_ids = {
        row[0]
        for row in bind.execute(existing_sql, {"provider": git_server_url, "type": provider_type})
    }

    # All users
    users_sql = sa.text("SELECT id, username, email, given_name, family_name FROM \"user\"")
    users = list(bind.execute(users_sql))

    with httpx.Client(
        base_url=git_server_url,
        auth=(admin_user, admin_pass),
        timeout=15.0,
    ) as client:
        # Probe connectivity before iterating all users
        try:
            probe = client.get("/api/v1/version")
            if not probe.is_success:
                logger.warning(f"Git server at {git_server_url} returned {probe.status_code} — skipping backfill")
                return
        except Exception as e:
            logger.warning(f"Git server at {git_server_url} is unreachable — skipping backfill ({e})")
            return

        for user_id, username, email, given_name, family_name in users:
            if user_id in existing_user_ids:
                continue

            # username column may be NULL for Keycloak-SSO-only users; derive from email
            git_username = username or (email and _username_from_email(email)) or str(user_id)
            display_name = (f"{given_name or ''} {family_name or ''}".strip()) or git_username
            safe_email = email or f"{git_username}@noreply.local"

            # Try to create; fall back to fetching if already exists
            git_user_data = None
            try:
                payload = {
                    "source_id": 0,
                    "login_name": git_username,
                    "username": git_username,
                    "email": safe_email,
                    "full_name": display_name,
                    "password": _generate_password(),
                    "must_change_password": False,
                    "send_notify": False,
                    "visibility": "private",
                }
                resp = client.post("/api/v1/admin/users", json=payload)
                if resp.status_code == 422:
                    # Already exists — fetch
                    r2 = client.get(f"/api/v1/users/{git_username}")
                    if r2.is_success:
                        git_user_data = r2.json()
                    else:
                        logger.warning(f"User {git_username} exists on git server but fetch failed: {r2.status_code}")
                        continue
                elif resp.is_success:
                    git_user_data = resp.json()
                else:
                    logger.warning(f"Failed to create git user {git_username}: {resp.status_code} {resp.text[:200]}")
                    continue
            except Exception as e:
                logger.warning(f"Git server error for {git_username}: {e}")
                continue

            if not git_user_data:
                continue

            git_username = git_user_data.get("login", git_username)
            git_user_id = git_user_data.get("id")

            try:
                bind.execute(
                    sa.text(
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
                        "props": json.dumps({"git_user_id": git_user_id}),
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to insert Account row for {git_username}: {e}")


def downgrade() -> None:
    git_server = os.environ.get("GIT_SERVER", "").strip()
    git_server_url = os.environ.get("GIT_SERVER_URL", "").strip()
    if not git_server or not git_server_url:
        return
    bind = op.get_bind()
    bind.execute(
        sa.text("DELETE FROM account WHERE provider = :provider AND type = :type"),
        {"provider": git_server_url, "type": git_server.lower()},
    )
