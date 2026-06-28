"""collapse student-repo modes to managed/external/download

Revision ID: 9e0fc5fef016
Revises: 61d25ae196fb
Create Date: 2026-06-28

The student-repo mode literals were provider-named and inconsistent. Collapse
them to provider-agnostic hosting modes (the provider comes from the bound
``GitServer.type``):

    forgejo, gitlab_managed  ->  managed
    gitlab_byo               ->  external
    download                 ->  download (unchanged)

Migrates ``course_member_repository.mode`` and ``course_git_binding.student_repo_modes``
and replaces the mode CHECK constraint. The downgrade recovers the provider flavour
from the bound git server's type.
"""
from typing import Sequence, Union

from alembic import op


revision: str = '9e0fc5fef016'
down_revision: Union[str, None] = '61d25ae196fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CONSTRAINT = 'course_member_repository_mode_check'
_TABLE = 'course_member_repository'


def upgrade() -> None:
    op.drop_constraint(_CONSTRAINT, _TABLE, type_='check')

    op.execute(
        "UPDATE course_member_repository SET mode = 'managed' "
        "WHERE mode IN ('forgejo', 'gitlab_managed')"
    )
    op.execute(
        "UPDATE course_member_repository SET mode = 'external' WHERE mode = 'gitlab_byo'"
    )
    op.execute(
        """
        UPDATE course_git_binding SET student_repo_modes = (
            SELECT to_jsonb(array_agg(DISTINCT m)) FROM (
                SELECT CASE
                    WHEN e IN ('forgejo', 'gitlab_managed') THEN 'managed'
                    WHEN e = 'gitlab_byo' THEN 'external'
                    ELSE e
                END AS m
                FROM jsonb_array_elements_text(student_repo_modes) AS e
            ) sub
        )
        WHERE student_repo_modes::text ~ '(forgejo|gitlab_managed|gitlab_byo)'
        """
    )

    op.create_check_constraint(
        _CONSTRAINT, _TABLE, "mode IN ('managed', 'external', 'download')"
    )


def downgrade() -> None:
    op.drop_constraint(_CONSTRAINT, _TABLE, type_='check')

    # Recover the provider flavour from the bound git server's type.
    op.execute(
        """
        UPDATE course_member_repository cmr SET mode = CASE
            WHEN cmr.mode = 'external' THEN 'gitlab_byo'
            WHEN cmr.mode = 'managed' AND EXISTS (
                SELECT 1 FROM git_server gs WHERE gs.id = cmr.git_server_id AND gs.type = 'gitlab'
            ) THEN 'gitlab_managed'
            WHEN cmr.mode = 'managed' THEN 'forgejo'
            ELSE cmr.mode
        END
        """
    )
    op.execute(
        """
        UPDATE course_git_binding b SET student_repo_modes = (
            SELECT to_jsonb(array_agg(DISTINCT m)) FROM (
                SELECT CASE
                    WHEN e = 'managed' AND EXISTS (
                        SELECT 1 FROM git_server gs WHERE gs.id = b.git_server_id AND gs.type = 'gitlab'
                    ) THEN 'gitlab_managed'
                    WHEN e = 'managed' THEN 'forgejo'
                    WHEN e = 'external' THEN 'gitlab_byo'
                    ELSE e
                END AS m
                FROM jsonb_array_elements_text(b.student_repo_modes) AS e
            ) sub
        )
        WHERE b.student_repo_modes::text ~ '(managed|external)'
        """
    )

    op.create_check_constraint(
        _CONSTRAINT, _TABLE,
        "mode IN ('forgejo', 'gitlab_managed', 'gitlab_byo', 'download')",
    )
