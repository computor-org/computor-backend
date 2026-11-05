"""``submission_feedback`` on course; grades without a human grader

``tests`` and ``tests_and_lena`` take the official test result as the grade as
soon as it is in; ``human`` keeps tutors grading. Existing courses keep today's
behaviour (``human``), except the public self-registration courses, which have
no tutors and start with ``tests``.

A grade the tests gave has no grader, so ``submission_grade.graded_by_course_member_id``
becomes nullable. The downgrade deletes those grades; the test results they
were taken from stay.

Revision ID: b8e4f1a2c3d9
Revises: c7d2e9f4a1b6
"""
from alembic import op
import sqlalchemy as sa


revision = 'b8e4f1a2c3d9'
down_revision = 'c7d2e9f4a1b6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'course',
        sa.Column('submission_feedback', sa.String(20), nullable=False, server_default=sa.text("'human'")),
    )
    op.create_check_constraint(
        'ck_course_submission_feedback',
        'course',
        "submission_feedback IN ('tests', 'tests_and_lena', 'human')",
    )
    op.execute("UPDATE course SET submission_feedback = 'tests' WHERE public")
    op.alter_column('submission_grade', 'graded_by_course_member_id', nullable=True)


def downgrade() -> None:
    op.execute("DELETE FROM submission_grade WHERE graded_by_course_member_id IS NULL")
    op.alter_column('submission_grade', 'graded_by_course_member_id', nullable=False)
    op.drop_constraint('ck_course_submission_feedback', 'course', type_='check')
    op.drop_column('course', 'submission_feedback')
