"""add builtin flag to account

Marks accounts that are part of the user's core identity (single sign-on,
Git server) as ``builtin``. These are created by the auth flow and must not
be unlinkable in the normal account-management UI. The flag is set in code
at creation time — there is no data backfill here.

Revision ID: a7f3b1c9d2e8
Revises: e4f5a6b7c8d9
Create Date: 2026-06-23
"""
from alembic import op
import sqlalchemy as sa


revision = 'a7f3b1c9d2e8'
down_revision = 'e4f5a6b7c8d9'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'account',
        sa.Column('builtin', sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade():
    op.drop_column('account', 'builtin')
