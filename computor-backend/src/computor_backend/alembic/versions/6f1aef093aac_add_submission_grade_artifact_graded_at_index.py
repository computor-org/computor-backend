"""add compound index on submission_grade(artifact_id, graded_at DESC)

Supports the DISTINCT ON (artifact_id) ORDER BY artifact_id, graded_at DESC
pattern used by get_unreviewed_submission_count_per_member. With this index
Postgres can scan only the first matching row per artifact instead of sorting
every grade.

Revision ID: 6f1aef093aac
Revises: 5cdba28b96de
Create Date: 2026-04-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6f1aef093aac'
down_revision: Union[str, None] = '5cdba28b96de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        'submission_grade_artifact_graded_at_idx',
        'submission_grade',
        ['artifact_id', sa.text('graded_at DESC')],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        'submission_grade_artifact_graded_at_idx',
        table_name='submission_grade',
    )
