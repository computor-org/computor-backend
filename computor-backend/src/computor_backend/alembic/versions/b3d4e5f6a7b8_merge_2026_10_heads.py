"""merge 2026.10 heads (session, minio-results, managed-repo-ref)

Collapses the three unmerged alembic heads on release/2026.10 into a single
head so that ``alembic upgrade head`` (used by api.sh / migrations.sh) resolves
to one target again. This migration performs no schema changes of its own — it
only converges the branches:

  - 32b313efe198  enhance_session_table_with_device_columns
  - a7b8c9d0e1f2  move_result_json_to_minio_storage
  - f7a1c2b3d4e5  unique_managed_repo_ref

Revision ID: b3d4e5f6a7b8
Revises: 32b313efe198, a7b8c9d0e1f2, f7a1c2b3d4e5
Create Date: 2026-07-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = ('32b313efe198', 'a7b8c9d0e1f2', 'f7a1c2b3d4e5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge the three heads. No schema changes."""
    pass


def downgrade() -> None:
    """Split back into the three prior heads. No schema changes."""
    pass
