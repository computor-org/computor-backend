"""add index on course_member.course_id

The compound unique index on (user_id, course_id) cannot seek on a
course_id-only predicate. Tutor/lecturer list endpoints filter members
by course_id, which would seq-scan the whole course_member table at
scale without a dedicated index.

Revision ID: 5cdba28b96de
Revises: d6691a076eef
Create Date: 2026-04-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '5cdba28b96de'
down_revision: Union[str, None] = 'd6691a076eef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        'ix_course_member_course_id',
        'course_member',
        ['course_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_course_member_course_id', table_name='course_member')
