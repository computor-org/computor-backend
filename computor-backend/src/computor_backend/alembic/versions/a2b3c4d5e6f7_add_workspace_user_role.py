"""add workspace_user and workspace_maintainer roles

Revision ID: a2b3c4d5e6f7
Revises: eb65f8f584b6
Create Date: 2026-02-05

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, None] = 'eb65f8f584b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO role (id, title, description, builtin)
        VALUES
            ('_workspace_user', 'Workspace User', 'Basic access to own workspaces: view, start, stop.', true),
            ('_workspace_maintainer', 'Workspace Maintainer', 'Full workspace management: provision, delete, manage all users.', true)
        ON CONFLICT (id) DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM role_claim WHERE role_id IN ('_workspace_user', '_workspace_maintainer');
        DELETE FROM user_role WHERE role_id IN ('_workspace_user', '_workspace_maintainer');
        DELETE FROM role WHERE id IN ('_workspace_user', '_workspace_maintainer');
    """)
