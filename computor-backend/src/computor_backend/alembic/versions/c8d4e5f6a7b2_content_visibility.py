"""Nullable ``visible`` on course and course_content, inherited down the tree

Issue #338. A lecturer needs to stage content before students may work on it:
prepare an exam unit invisibly, rehearse it through the real student path,
reveal it for the exam, then hide it again.

``visible`` is a *veto*, not a nearest-non-NULL fallback like the budget
columns added in a7f3c9d2e451:

    effective_visible(node) = course.visible IS NOT FALSE
                              AND no ancestor-or-self has visible = FALSE

NULL (the default everywhere, hence no backfill) means inherit. False anywhere
in the chain hides the whole subtree. True on a child cannot re-grant what an
ancestor denied.

The GiST index is what makes the ancestor predicate usable. ``course_content``
has only a btree on (course_id, path) today, which cannot serve the ltree
``<@`` containment operator that the resolver's NOT EXISTS relies on.

Revision ID: c8d4e5f6a7b2
Revises: a7f3c9d2e451
"""
from alembic import op
import sqlalchemy as sa


revision = 'c8d4e5f6a7b2'
down_revision = 'a7f3c9d2e451'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('course', sa.Column('visible', sa.Boolean(), nullable=True))
    op.add_column('course_content', sa.Column('visible', sa.Boolean(), nullable=True))

    # NULL everywhere is exactly the intended starting state: everything
    # inherits, everything is visible. No backfill.

    op.create_index(
        'ix_course_content_path_gist',
        'course_content',
        ['path'],
        postgresql_using='gist',
    )


def downgrade() -> None:
    op.drop_index('ix_course_content_path_gist', table_name='course_content')
    op.drop_column('course_content', 'visible')
    op.drop_column('course', 'visible')
