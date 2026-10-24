"""Persist optional finite course ordering.

Revision ID: d9f4a6b8c0e3
Revises: c8e3f5a7b9d2
"""
from alembic import op
import sqlalchemy as sa

revision = 'd9f4a6b8c0e3'
down_revision = 'c8e3f5a7b9d2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('course', sa.Column('position', sa.Float(53), nullable=True))
    op.create_check_constraint(
        'ck_course_position_finite', 'course',
        "position > '-Infinity'::double precision AND position < 'Infinity'::double precision",
    )


def downgrade() -> None:
    op.drop_constraint('ck_course_position_finite', 'course', type_='check')
    op.drop_column('course', 'position')
