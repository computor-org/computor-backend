"""make message title nullable

Revision ID: c5580e965cdd
Revises: a2b3c4d5e6f7
Create Date: 2026-03-24 16:54:14.874140

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5580e965cdd'
down_revision: Union[str, None] = 'a2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('message', 'title',
               existing_type=sa.VARCHAR(length=255),
               nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('message', 'title',
               existing_type=sa.VARCHAR(length=255),
               nullable=False)
