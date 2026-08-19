"""Course-level test/submission defaults; submission group limits become overrides

Two related changes behind issue #337 ("limits for tests and submissions not
honoured"):

1. ``course`` gains ``max_test_runs`` / ``max_submissions`` as course-wide
   defaults. Resolution is now three-tiered — submission group override, then
   course content, then course default, then unlimited.

2. The matching ``submission_group`` columns stop being a snapshot and become a
   deliberate per-group override. They used to be copied from the course
   content when the group was created, and enforcement read only that copy, so
   a lecturer editing a limit never reached students who had already started.

   The data step clears both columns. Every value in them today is a copy by
   construction: ``max_test_runs`` was not writable through any DTO at all, and
   while ``max_submissions`` was reachable via ``PATCH /submission-groups/{id}``,
   no UI in any repo writes it. Clearing them makes every existing group
   inherit its assignment's configured limit, which is what a lecturer already
   expects to have set.

Revision ID: a7f3c9d2e451
Revises: b5c6d7e8f9a0
"""
from alembic import op
import sqlalchemy as sa


revision = 'a7f3c9d2e451'
down_revision = 'b5c6d7e8f9a0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('course', sa.Column('max_test_runs', sa.Integer(), nullable=True))
    op.add_column('course', sa.Column('max_submissions', sa.Integer(), nullable=True))

    # Drop the stale snapshots so the effective limit is resolved from the
    # course content (and the new course default) from now on.
    op.execute(
        "UPDATE submission_group SET max_test_runs = NULL WHERE max_test_runs IS NOT NULL"
    )
    op.execute(
        "UPDATE submission_group SET max_submissions = NULL WHERE max_submissions IS NOT NULL"
    )


def downgrade() -> None:
    # The cleared values were stale copies, so there is nothing faithful to
    # restore: re-copying from course_content would re-freeze today's values
    # rather than the ones that were there before. Only the schema is reverted.
    op.drop_column('course', 'max_submissions')
    op.drop_column('course', 'max_test_runs')
