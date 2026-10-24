"""Builtin course role ``_inactive`` for learners who left a course

A self-enrolled learner can now leave a course (issues#458). The membership
row cannot be deleted, because submissions and results reference it, so its
role becomes ``_inactive``. The role is outside the course role hierarchy and
grants nothing; joining the course again restores ``_student``.

Revision ID: c8e3f5a7b9d2
Revises: b7d2e4f6a8c1
"""
from alembic import op


revision = 'c8e3f5a7b9d2'
down_revision = 'b7d2e4f6a8c1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO course_role (id, title, description, builtin)
        VALUES ('_inactive', 'Inactive', 'Former learner who left the course; grants no access.', true)
        ON CONFLICT (id) DO NOTHING;
    """)


def downgrade() -> None:
    # Without the role the memberships cannot stay; they become students again,
    # which is what they were before this revision.
    op.execute("UPDATE course_member SET course_role_id = '_student' WHERE course_role_id = '_inactive'")
    op.execute("DELETE FROM course_role WHERE id = '_inactive'")
