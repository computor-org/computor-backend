"""Per-language title and description maps on course families.

Course families kept one title, so "Data Science mit Python" showed in the
breadcrumb of an English reader. Nullable JSONB maps as on course
(a3f8c1d6e9b4): ``title``/``description`` stay the source text and fallback.

Revision ID: c7d2e9f4a1b6
Revises: e4b7c9d1f2a3
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'c7d2e9f4a1b6'
down_revision = 'e4b7c9d1f2a3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('course_family', sa.Column('title_i18n', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('course_family', sa.Column('description_i18n', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('course_family', 'description_i18n')
    op.drop_column('course_family', 'title_i18n')
