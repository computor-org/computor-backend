"""denormalise course_content_kind_id and is_submittable on course_content

Revision ID: e0f1a2b3c4d5
Revises: d9e0f1a2b3c4
Create Date: 2026-04-29 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e0f1a2b3c4d5'
down_revision: Union[str, None] = 'd9e0f1a2b3c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Replace the ``column_property(scalar_subquery())`` definitions
    on ``CourseContent`` with real columns (#121).

    The Python-side definition was forcing Postgres to re-execute a
    correlated subquery against ``course_content_type → course_content_kind``
    once per materialised row (visible as ``SubPlan 2`` / ``SubPlan 3``
    in EXPLAIN, with ``loops`` equal to the row count). The data is
    structurally fixed at content-creation time, so a real column +
    backfill + ``before_insert``/``before_update`` listener (in the
    SQLAlchemy model) is the right shape.

    Strategy:
      1. Add nullable columns + supporting index.
      2. Backfill from the existing relationship chain.
      3. Set NOT NULL.
      4. Add the FK constraint (deferred so the backfill UPDATE doesn't
         have to satisfy it row-by-row mid-migration).
    """
    # 1. Add nullable columns. ``server_default`` on is_submittable so
    #    existing rows aren't rejected before the backfill UPDATE runs.
    op.add_column(
        'course_content',
        sa.Column(
            'course_content_kind_id',
            sa.String(length=255),
            nullable=True,
        ),
    )
    op.add_column(
        'course_content',
        sa.Column(
            'is_submittable',
            sa.Boolean(),
            nullable=True,
        ),
    )

    # Helpful index for the FK + future joins; kept partial-free since
    # this column is meant to be set on every row after the backfill.
    op.create_index(
        'ix_course_content_course_content_kind_id',
        'course_content',
        ['course_content_kind_id'],
    )

    # 2. Backfill from the chain: course_content → course_content_type
    #    → course_content_kind.
    op.execute(
        """
        UPDATE course_content cc
           SET course_content_kind_id = cct.course_content_kind_id,
               is_submittable         = cck.submittable
          FROM course_content_type cct
          JOIN course_content_kind cck ON cck.id = cct.course_content_kind_id
         WHERE cct.id = cc.course_content_type_id;
        """
    )

    # 3. Set NOT NULL. ``is_submittable`` also gets a server_default so
    #    future inserts that bypass the SQLAlchemy listener (raw SQL,
    #    other tooling) don't fail the constraint — the listener
    #    overrides the default with the correct value.
    op.alter_column(
        'course_content',
        'course_content_kind_id',
        existing_type=sa.String(length=255),
        nullable=False,
    )
    op.alter_column(
        'course_content',
        'is_submittable',
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text('false'),
    )

    # 4. FK constraint. ON UPDATE CASCADE so that if a kind is renamed,
    #    referencing rows update; ON DELETE RESTRICT so we don't lose
    #    course content silently if a kind is removed.
    op.create_foreign_key(
        'fk_course_content_course_content_kind_id',
        'course_content',
        'course_content_kind',
        ['course_content_kind_id'],
        ['id'],
        onupdate='CASCADE',
        ondelete='RESTRICT',
    )


def downgrade() -> None:
    op.drop_constraint(
        'fk_course_content_course_content_kind_id',
        'course_content',
        type_='foreignkey',
    )
    op.drop_index(
        'ix_course_content_course_content_kind_id',
        table_name='course_content',
    )
    op.drop_column('course_content', 'is_submittable')
    op.drop_column('course_content', 'course_content_kind_id')
