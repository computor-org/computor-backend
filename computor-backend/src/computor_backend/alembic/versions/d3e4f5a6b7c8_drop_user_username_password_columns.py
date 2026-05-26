"""drop user username, password, password_reset_required columns

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-05-25

Authentication is now exclusively via Keycloak SSO. Local username/password
auth has been removed. These columns are no longer written or read by any
application code, so they are safe to drop.

Production safety: this migration only drops columns. If a rollback is needed,
the columns can be re-added (data will be lost — but they were never populated
in Keycloak-only mode).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd3e4f5a6b7c8'
down_revision: Union[str, None] = 'c2d3e4f5a6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # user_username_key is a UNIQUE constraint; Postgres backs it with an index
    # of the same name that cannot be dropped directly (DependentObjectsStillExist).
    # Dropping the constraint removes the backing index too.
    op.execute('ALTER TABLE "user" DROP CONSTRAINT IF EXISTS user_username_key')
    op.drop_column('user', 'username')
    op.drop_column('user', 'password')
    op.drop_column('user', 'password_reset_required')


def downgrade() -> None:
    op.add_column('user', sa.Column('password_reset_required', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('user', sa.Column('password', sa.String(length=512), nullable=True))
    op.add_column('user', sa.Column('username', sa.String(length=255), nullable=True))
    op.create_unique_constraint('user_username_key', 'user', ['username'])
