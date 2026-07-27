"""add service_manager role

Adds the ``_service_manager`` builtin role so managing machine identities
(testing workers, integrations, AI agents) and their API tokens can be
delegated without granting ``_admin``.

The claims themselves are applied idempotently at API startup by
``db_apply_roles("_service_manager", claims_service_manager(), db)`` in
``server.py`` — this migration only has to make the role row exist, which
mirrors ``a3b4c5d6e7f8_add_git_manager_role``.

Revision ID: c7d8e9f0a1b2
Revises: f2a3b4c5d6e7
Create Date: 2026-07-27

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'c7d8e9f0a1b2'
down_revision: Union[str, None] = 'f2a3b4c5d6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO role (id, title, description, builtin)
        VALUES (
            '_service_manager',
            'Service Manager',
            'Manage service accounts (testing workers, integrations, AI agents) and their API tokens, without full admin.',
            true
        )
        ON CONFLICT (id) DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM role_claim WHERE role_id = '_service_manager';
        DELETE FROM user_role WHERE role_id = '_service_manager';
        DELETE FROM role WHERE id = '_service_manager';
    """)
