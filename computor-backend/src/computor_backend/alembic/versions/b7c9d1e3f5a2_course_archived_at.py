"""Nullable ``archived_at`` on course

An owner archives a course at the end of its life instead of deleting it:
archived courses vanish from the student and tutor views and the public
catalog, and student writes (submissions, test runs) are refused through the
same veto ``visible`` uses. Deleting a course that holds student submissions
requires it to be archived first, and even then only an administrator may.

``Organization`` has carried the same column since the initial schema;
``course_family`` deliberately does not get one (its lifecycle is its
courses').

Revision ID: b7c9d1e3f5a2
Revises: 2e14e73b0442
"""
from alembic import op
import sqlalchemy as sa


revision = 'b7c9d1e3f5a2'
down_revision = '2e14e73b0442'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('course', sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('course', 'archived_at')
