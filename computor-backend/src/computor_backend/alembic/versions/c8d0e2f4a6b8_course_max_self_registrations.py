"""Nullable ``max_self_registrations`` on course

Caps how many ``_student`` members a public course accepts through
self-registration. NULL (every existing row) means unlimited, so the upgrade
changes no behaviour until a lecturer sets a number.

Revision ID: c8d0e2f4a6b8
Revises: b7c9d1e3f5a2
"""
from alembic import op
import sqlalchemy as sa


revision = 'c8d0e2f4a6b8'
down_revision = 'b7c9d1e3f5a2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('course', sa.Column('max_self_registrations', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('course', 'max_self_registrations')
