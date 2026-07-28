"""add per-user key version for the workspace app credential

The credential every workspace app requires is DERIVED, not stored:
HMAC(TOKEN_SECRET, context + user_id). That gives us no migration and no
secret at rest on our side, but it also left no way to revoke one person's
credential — the only levers were rotating TOKEN_SECRET, which re-keys every
encrypted git token on the platform, or bumping the shared context string,
which invalidates everyone at once.

The key version joins the HMAC message, so bumping it changes exactly one
user's secret. Version 1 reproduces the original derivation byte for byte, so
existing workspaces keep working and the column can default to 1 for every
row. ``rotated_at`` is audit only — who asked is in the application log.

Revision ID: a4b5c6d7e8f9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a4b5c6d7e8f9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'user',
        sa.Column(
            'workspace_app_key_version',
            sa.Integer(),
            server_default=sa.text('1'),
            nullable=False,
        ),
    )
    op.add_column(
        'user',
        sa.Column('workspace_app_key_rotated_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('user', 'workspace_app_key_rotated_at')
    op.drop_column('user', 'workspace_app_key_version')
