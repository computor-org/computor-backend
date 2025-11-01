"""remove_legacy_user_fields

Revision ID: a5d4bb78da7a
Revises: a1b2c3d4e5f7
Create Date: 2025-11-01 15:00:36.371007

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a5d4bb78da7a'
down_revision: Union[str, None] = 'a1b2c3d4e5f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - remove legacy user fields."""

    # Drop the check constraint first
    op.drop_constraint('ck_user_token_expiration', 'user', type_='check')

    # Drop columns
    op.drop_column('user', 'number')
    op.drop_column('user', 'fs_number')
    op.drop_column('user', 'auth_token')
    op.drop_column('user', 'token_expiration')
    op.drop_column('user', 'user_type')


def downgrade() -> None:
    """Downgrade schema - restore legacy user fields."""

    # Restore columns
    op.add_column('user', sa.Column('user_type', sa.Enum('user', 'token', name='user_type'), nullable=False, server_default=sa.text("'user'::user_type")))
    op.add_column('user', sa.Column('token_expiration', sa.DateTime(timezone=True), nullable=True))
    op.add_column('user', sa.Column('auth_token', sa.String(4096), nullable=True))
    op.add_column('user', sa.Column('fs_number', sa.BigInteger, nullable=False, server_default=sa.text("nextval('user_unique_fs_number_seq'::regclass)")))
    op.add_column('user', sa.Column('number', sa.String(255), nullable=True))

    # Restore unique constraint on number
    op.create_unique_constraint(None, 'user', ['number'])

    # Restore check constraint
    op.create_check_constraint('ck_user_token_expiration', 'user', "(user_type <> 'token') OR (token_expiration IS NOT NULL)")
