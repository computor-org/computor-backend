"""update_service_slug_constraint_allow_dots

Revision ID: a1b2c3d4e5f7
Revises: 70413c285ac5
Create Date: 2025-10-29 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, None] = '70413c285ac5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - allow dots in service slugs."""
    # Drop the old constraint
    op.drop_constraint('ck_service_slug_format', 'service', type_='check')

    # Add the new constraint that allows dots
    op.create_check_constraint(
        'ck_service_slug_format',
        'service',
        "slug ~* '^[a-z0-9][a-z0-9.\\-]*[a-z0-9]$'"
    )


def downgrade() -> None:
    """Downgrade schema - revert to original slug pattern."""
    # Drop the new constraint
    op.drop_constraint('ck_service_slug_format', 'service', type_='check')

    # Restore the old constraint (hyphens only, no dots)
    op.create_check_constraint(
        'ck_service_slug_format',
        'service',
        "slug ~* '^[a-z0-9][a-z0-9-]*[a-z0-9]$'"
    )
