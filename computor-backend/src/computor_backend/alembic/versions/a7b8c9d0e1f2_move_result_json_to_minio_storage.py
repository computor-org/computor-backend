"""move_result_json_to_minio_storage

Revision ID: a7b8c9d0e1f2
Revises: 059601a6c7ef
Create Date: 2025-10-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, None] = '059601a6c7ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Move result_json from database to MinIO storage.

    The result_json field is dropped from the result table.
    Going forward, result JSON data will be stored in MinIO at:
    results/{result_id}/result.json

    Note: Existing result_json data is NOT migrated to MinIO.
    This is intentional as per requirements.
    """
    # Drop the result_json column from result table
    op.drop_column('result', 'result_json')


def downgrade() -> None:
    """
    Restore result_json column to database.

    Note: This will recreate the column but data stored in MinIO
    will NOT be migrated back to the database column.
    """
    # Re-add the result_json column
    op.add_column('result', sa.Column('result_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
