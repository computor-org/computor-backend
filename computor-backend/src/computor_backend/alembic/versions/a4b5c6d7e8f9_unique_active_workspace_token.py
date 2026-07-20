"""unique active workspace auto-login token per (user, name)

Revision ID: a4b5c6d7e8f9
Revises: f2a3b4c5d6e7
Create Date: 2026-07-20

Workspace auto-login tokens ("workspace-auto-login:{workspace}") are meant to
be per-workspace singletons, but that was enforced only by a lookup-then-revoke
in mint_workspace_token — a stale repository cache or two concurrent provisions
could leave several active tokens for the same workspace. Adds a PARTIAL unique
index on ``(user_id, name)`` scoped to active workspace tokens. User-created
personal tokens may legitimately share a name and are exempt.

Existing duplicates (accumulated through the cache bug) are revoked first,
keeping only the newest active token per (user, name) — the newest is the one
actually deployed in the workspace.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a4b5c6d7e8f9'
down_revision: Union[str, None] = 'f2a3b4c5d6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEX = 'uq_api_token_active_workspace_name'
_TABLE = 'api_token'


def upgrade() -> None:
    conn = op.get_bind()
    # Keep the newest active token per (user_id, name) — it is the one whose
    # plaintext the workspace actually holds — and revoke the older leftovers.
    result = conn.execute(sa.text(
        """
        UPDATE api_token SET
            revoked_at = now(),
            revocation_reason = 'duplicate active workspace token (migration cleanup)'
        WHERE id IN (
            SELECT id FROM (
                SELECT id, ROW_NUMBER() OVER (
                    PARTITION BY user_id, name
                    ORDER BY created_at DESC, id DESC
                ) AS rn
                FROM api_token
                WHERE revoked_at IS NULL
                  AND name LIKE 'workspace-auto-login%'
            ) ranked
            WHERE rn > 1
        )
        """
    ))
    if result.rowcount:
        print(f"Revoked {result.rowcount} duplicate active workspace token(s)")

    op.create_index(
        _INDEX,
        _TABLE,
        ['user_id', 'name'],
        unique=True,
        postgresql_where=sa.text(
            "revoked_at IS NULL AND name LIKE 'workspace-auto-login%'"
        ),
    )


def downgrade() -> None:
    # Tokens revoked by the upgrade cleanup are not restored — they were
    # superseded duplicates whose plaintext no workspace holds anymore.
    op.drop_index(_INDEX, table_name=_TABLE)
