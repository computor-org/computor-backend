"""Per-language title and description maps.

``title``/``description`` hold one string, so a course released in German shows
German titles to an English reader and the clients patch around it
(computor-org/issues#550). These nullable JSONB maps carry the other languages
alongside it -- ``{"de": "...", "en": "..."}`` -- while the existing columns
stay the source text and the fallback every old client keeps reading.

Revision ID: a3f8c1d6e9b4
Revises: d9f4a6b8c0e3
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'a3f8c1d6e9b4'
down_revision = 'd9f4a6b8c0e3'
branch_labels = None
depends_on = None

_TABLES = ('course', 'course_content', 'course_content_type', 'example', 'example_version')


# The example models document each meta.yaml-backed column in a comment.
_COMMENTS = {
    'example': ('meta.yaml: title_i18n', 'meta.yaml: description_i18n'),
    'example_version': ('meta.yaml: title_i18n (per-version)', 'meta.yaml: description_i18n (per-version)'),
}


def upgrade() -> None:
    for table in _TABLES:
        title_comment, description_comment = _COMMENTS.get(table, (None, None))
        op.add_column(table, sa.Column('title_i18n', postgresql.JSONB(astext_type=sa.Text()),
                                       nullable=True, comment=title_comment))
        op.add_column(table, sa.Column('description_i18n', postgresql.JSONB(astext_type=sa.Text()),
                                       nullable=True, comment=description_comment))


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.drop_column(table, 'description_i18n')
        op.drop_column(table, 'title_i18n')
