"""remove unique constraint on submission_artifact version_identifier

Revision ID: 3735092f2fc3
Revises: a1b2c3d4e5f6
Create Date: 2025-10-09 01:05:19.429311

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3735092f2fc3'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Remove unique constraint to allow multiple artifacts per version."""
    # Drop the unique constraint that prevents multiple artifacts per version_identifier
    op.drop_constraint('uq_submission_artifact_group_version', 'submission_artifact', type_='unique')

    # Keep the index for query performance
    # Index 'submission_artifact_group_version_idx' already exists and will remain


def downgrade() -> None:
    """Downgrade schema: Restore unique constraint."""
    # Recreate the unique constraint
    op.create_unique_constraint('uq_submission_artifact_group_version', 'submission_artifact', ['submission_group_id', 'version_identifier'])
