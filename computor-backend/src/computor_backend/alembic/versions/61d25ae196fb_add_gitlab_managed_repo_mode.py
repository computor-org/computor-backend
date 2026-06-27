"""add gitlab_managed to course_member_repository.mode check

Revision ID: 61d25ae196fb
Revises: e7f8a9b0c1d2
Create Date: 2026-06-27

Adds the ``gitlab_managed`` student-repo mode (system-provisioned repositories
on a managed GitLab instance, access granted via the backend's group token) to
the ``course_member_repository_mode_check`` constraint.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '61d25ae196fb'
down_revision: Union[str, None] = 'e7f8a9b0c1d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_CONSTRAINT = 'course_member_repository_mode_check'
_TABLE = 'course_member_repository'


def upgrade() -> None:
    op.drop_constraint(_CONSTRAINT, _TABLE, type_='check')
    op.create_check_constraint(
        _CONSTRAINT,
        _TABLE,
        "mode IN ('forgejo', 'gitlab_managed', 'gitlab_byo', 'download')",
    )


def downgrade() -> None:
    op.drop_constraint(_CONSTRAINT, _TABLE, type_='check')
    op.create_check_constraint(
        _CONSTRAINT,
        _TABLE,
        "mode IN ('forgejo', 'gitlab_byo', 'download')",
    )
