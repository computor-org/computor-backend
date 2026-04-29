"""add partial index for latest-submitted-artifact-per-group lookups

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
Create Date: 2026-04-29 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'd9e0f1a2b3c4'
down_revision: Union[str, None] = 'c8d9e0f1a2b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add partial covering index for the hot "latest submitted artifact"
    aggregation in the tutor/student course-content list query (#119).

    The aggregation
        SELECT submission_group_id, MAX(created_at)
          FROM submission_artifact
          WHERE submit = TRUE
          GROUP BY submission_group_id
    runs at least once per call to ``course_member_course_content_list_query``
    and ``user_course_content_list_query``. With this partial index Postgres
    can satisfy the GROUP BY MAX via an index-only scan rather than a heap
    scan + filter + sort.

    Existing ``submission_artifact_submission_group_idx`` covers the FK
    join but not the ``submit = TRUE`` predicate or the per-group MAX.
    """
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_submission_artifact_group_created_submitted
          ON submission_artifact (submission_group_id, created_at DESC)
          WHERE submit = TRUE;
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP INDEX IF EXISTS idx_submission_artifact_group_created_submitted;"
    )
