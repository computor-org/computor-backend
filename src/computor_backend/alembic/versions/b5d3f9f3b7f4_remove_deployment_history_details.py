"""remove redundant deployment history fields

Revision ID: b5d3f9f3b7f4
Revises: 9b7a6f4f4a1d
Create Date: 2025-03-12 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'b5d3f9f3b7f4'
down_revision = '9b7a6f4f4a1d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column('deployment_history', 'meta')
    op.drop_column('deployment_history', 'action_details')


def downgrade() -> None:
    op.add_column(
        'deployment_history',
        sa.Column(
            'action_details',
            sa.Text(),
            nullable=True,
            comment='Detailed description of the action',
        ),
    )
    op.add_column(
        'deployment_history',
        sa.Column(
            'meta',
            postgresql.JSONB(),
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
            comment='Additional metadata about the action',
        ),
    )
