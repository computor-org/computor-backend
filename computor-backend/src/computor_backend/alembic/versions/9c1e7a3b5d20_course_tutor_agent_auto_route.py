"""``tutor_agent_auto_route`` flag on course

When set, a student's course message that mentions nobody is addressed to the
configured tutor agent (Lena) with a visible @mention. NOT NULL with a false
default, so every existing course keeps today's behaviour.

Revision ID: 9c1e7a3b5d20
Revises: a5b6c7d8e9f0
"""
from alembic import op
import sqlalchemy as sa


revision = '9c1e7a3b5d20'
down_revision = 'a5b6c7d8e9f0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'course',
        sa.Column('tutor_agent_auto_route', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )


def downgrade() -> None:
    op.drop_column('course', 'tutor_agent_auto_route')
