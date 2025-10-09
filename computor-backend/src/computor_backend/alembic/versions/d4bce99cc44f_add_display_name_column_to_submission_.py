"""add display_name column to submission_group

Revision ID: d4bce99cc44f
Revises: 3735092f2fc3
Create Date: 2025-10-09 11:06:41.102861

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4bce99cc44f'
down_revision: Union[str, None] = '3735092f2fc3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Add display_name column to submission_group."""
    # Add display_name column
    op.add_column('submission_group', sa.Column('display_name', sa.String(length=255), nullable=True))

    # Note: display_name is nullable - it will be NULL initially
    # For individual submissions (max_group_size = 1), it will be auto-computed from student name
    # For team submissions, it should be manually set


def downgrade() -> None:
    """Downgrade schema: Remove display_name column."""
    op.drop_column('submission_group', 'display_name')
