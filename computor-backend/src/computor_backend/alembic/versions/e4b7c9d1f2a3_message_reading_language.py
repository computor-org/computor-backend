"""Store the author's reading language with each message.

Revision ID: e4b7c9d1f2a3
Revises: a3f8c1d6e9b4
"""
from alembic import op
import sqlalchemy as sa

revision = 'e4b7c9d1f2a3'
down_revision = 'a3f8c1d6e9b4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('message', sa.Column('reading_language', sa.String(2), nullable=True))


def downgrade() -> None:
    op.drop_column('message', 'reading_language')
