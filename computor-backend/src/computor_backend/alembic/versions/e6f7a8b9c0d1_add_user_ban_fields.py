"""add ban fields to user

Adds ``banned_at`` (timestamptz) and ``ban_reason`` (varchar) to the ``user``
table. A non-null ``banned_at`` marks the user as banned and blocks them from
authenticating (enforced in ``PrincipalBuilder.build`` and the SSO callback).
Mirrors the existing ``archived_at`` soft-marker pattern — both columns are
nullable, so no backfill is required (NULL = not banned).

Revision ID: e6f7a8b9c0d1
Revises: c4e5f6a7b8c9
Create Date: 2026-07-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6f7a8b9c0d1'
down_revision: Union[str, None] = 'c4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the ban marker columns to the user table."""
    op.add_column('user', sa.Column('banned_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('user', sa.Column('ban_reason', sa.String(length=1024), nullable=True))


def downgrade() -> None:
    """Remove the ban marker columns from the user table."""
    op.drop_column('user', 'ban_reason')
    op.drop_column('user', 'banned_at')
