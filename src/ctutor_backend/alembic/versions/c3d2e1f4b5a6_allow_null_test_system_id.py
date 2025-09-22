"""allow null test_system_id on results

Revision ID: c3d2e1f4b5a6
Revises: b5d3f9f3b7f4
Create Date: 2025-05-18 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3d2e1f4b5a6'
down_revision = 'b5d3f9f3b7f4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        'result',
        'test_system_id',
        existing_type=sa.String(length=255),
        nullable=True,
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE result
        SET test_system_id = 'manual-' || id::text
        WHERE test_system_id IS NULL
        """
    )
    op.alter_column(
        'result',
        'test_system_id',
        existing_type=sa.String(length=255),
        nullable=False,
    )

