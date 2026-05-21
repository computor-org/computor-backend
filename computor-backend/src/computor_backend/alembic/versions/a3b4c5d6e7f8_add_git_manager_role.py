"""add git_manager role

Revision ID: a3b4c5d6e7f8
Revises: cc1d2e3f4a5b
Create Date: 2026-05-21

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'a3b4c5d6e7f8'
down_revision: Union[str, None] = 'cc1d2e3f4a5b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO role (id, title, description, builtin)
        VALUES ('_git_manager', 'Git Manager', 'Full access to git server user management via the /git/* endpoints.', true)
        ON CONFLICT (id) DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM role_claim WHERE role_id = '_git_manager';
        DELETE FROM user_role WHERE role_id = '_git_manager';
        DELETE FROM role WHERE id = '_git_manager';
    """)
