"""backfill message course_content_id from submission_group

Revision ID: d6691a076eef
Revises: c5580e965cdd
Create Date: 2026-03-30 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'd6691a076eef'
down_revision: Union[str, None] = 'c5580e965cdd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Backfill course_content_id on messages that have submission_group_id set.

    The application now auto-populates course_content_id when creating
    submission_group-scoped messages. This migration backfills existing
    messages that were created before this change.
    """
    op.execute("""
        UPDATE message m
        SET course_content_id = sg.course_content_id
        FROM submission_group sg
        WHERE m.submission_group_id = sg.id
          AND m.course_content_id IS NULL
          AND sg.course_content_id IS NOT NULL
    """)


def downgrade() -> None:
    """Remove backfilled course_content_id from submission_group messages.

    Only clears course_content_id where it matches the submission_group's
    course_content_id (i.e., was auto-populated, not explicitly set).
    """
    op.execute("""
        UPDATE message m
        SET course_content_id = NULL
        FROM submission_group sg
        WHERE m.submission_group_id = sg.id
          AND m.course_content_id = sg.course_content_id
    """)
