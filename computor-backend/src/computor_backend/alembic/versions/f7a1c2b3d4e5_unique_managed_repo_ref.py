"""unique managed (git_server, repo_ref) on course_member_repository

Revision ID: f7a1c2b3d4e5
Revises: 9e0fc5fef016
Create Date: 2026-06-30

Backstop against student-repo name collisions: a managed repo name that already
exists for another course member must fail loudly, not silently share one repo.
Adds a PARTIAL unique index on ``(git_server_id, repo_ref)`` scoped to
``mode = 'managed' AND repo_ref IS NOT NULL`` (BYO/download rows and NULL refs
are exempt). Pre-checks for existing duplicates and aborts with a clear message
rather than failing opaquely on index creation.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f7a1c2b3d4e5'
down_revision: Union[str, None] = '9e0fc5fef016'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEX = 'course_member_repository_managed_ref_key'
_TABLE = 'course_member_repository'


def upgrade() -> None:
    conn = op.get_bind()
    dupes = conn.execute(sa.text(
        """
        SELECT git_server_id, repo_ref, COUNT(*) AS n
        FROM course_member_repository
        WHERE mode = 'managed' AND repo_ref IS NOT NULL
        GROUP BY git_server_id, repo_ref
        HAVING COUNT(*) > 1
        """
    )).fetchall()
    if dupes:
        listed = ", ".join(f"{r.git_server_id}/{r.repo_ref} (x{r.n})" for r in dupes)
        raise RuntimeError(
            "Cannot add unique index: existing duplicate managed repo refs must be "
            f"resolved first: {listed}"
        )

    op.create_index(
        _INDEX,
        _TABLE,
        ['git_server_id', 'repo_ref'],
        unique=True,
        postgresql_where=sa.text("mode = 'managed' AND repo_ref IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(_INDEX, table_name=_TABLE)
