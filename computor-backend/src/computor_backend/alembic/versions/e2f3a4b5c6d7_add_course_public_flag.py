"""Course.public — the flag that lists a course in the self-registration catalog

A public course appears in ``GET /courses/public`` and any signed-in user may
create their own ``_student`` membership in it (issue #213).

NOT NULL DEFAULT false, unlike ``visible`` (added in c8d4e5f6a7b2), which is a
tri-state veto resolved up the content tree. There is nothing for ``public`` to
inherit from, so a third "unset" state would be indistinguishable from false
and every catalog query would have to spell out IS NOT TRUE. No backfill: false
everywhere is exactly the intended starting state.

The partial index keeps the catalog off a sequential scan. The predicate is the
most selective one on the table (almost no course is public), it is evaluated on
every catalog page load, and indexing ``title`` under it also serves the
endpoint's ORDER BY. Being partial, it costs almost nothing to maintain.

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
"""
from alembic import op
import sqlalchemy as sa


revision = 'e2f3a4b5c6d7'
down_revision = 'd1e2f3a4b5c6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'course',
        sa.Column('public', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )
    op.create_index(
        'ix_course_public_title',
        'course',
        ['title'],
        postgresql_where=sa.text('public'),
    )


def downgrade() -> None:
    op.drop_index('ix_course_public_title', table_name='course')
    op.drop_column('course', 'public')
