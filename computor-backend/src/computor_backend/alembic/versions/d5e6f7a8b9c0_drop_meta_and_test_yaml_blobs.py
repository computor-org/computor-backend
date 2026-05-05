"""drop meta JSONB and test_yaml text from example_version

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-05-05 14:00:00.000000

The previous refactor (c4d5e6f7a8b9) replaced the legacy ``meta_yaml``
text column with a ``meta`` JSONB plus promoted scalar/array columns.
After review we decided ``meta`` JSONB and ``test_yaml`` text are
redundant: every example file (including ``meta.yaml`` and
``test.yaml``) is already persisted to MinIO at
``{storage_path}/{filename}``. The promoted columns
(``title``, ``description``, ``language``, ``license``,
``execution_backend``, ``student_submission_files``,
``additional_files``, ``student_templates``, ``test_files``,
``testing_service_id``) cover every hot-path read; the download
endpoint reads the original yaml documents from MinIO with a Redis
cache in front for the cold path.

Drops only — no data migration. The yaml documents themselves still
exist in MinIO.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, None] = 'c4d5e6f7a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('example_version', 'meta')
    op.drop_column('example_version', 'test_yaml')


def downgrade() -> None:
    """Re-create the columns as nullable. No backfill — yaml documents
    live in MinIO and would have to be re-fetched. Downgrade is for
    schema rollback only."""
    op.add_column(
        'example_version',
        sa.Column('test_yaml', sa.Text(), nullable=True),
    )
    op.add_column(
        'example_version',
        sa.Column('meta', postgresql.JSONB(), nullable=True),
    )
