"""merge argon2 and message audit branches

Revision ID: d32f835b7227
Revises: 2bcd79895e02, b2c3d4e5f6a7
Create Date: 2025-10-24 15:52:33.352680

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd32f835b7227'
down_revision: Union[str, None] = ('2bcd79895e02', 'b2c3d4e5f6a7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
