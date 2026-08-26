"""add instance_settings (deployment-wide admission limits)

Creates the singleton table behind #351's two limits — max concurrent
workspace users and max concurrent logins — plus the idle window that decides
how long a login seat is held after the user's last request.

Deliberately a table and not environment variables: the limits have to be
tunable during a running workshop without a redeploy.

No row is inserted. An absent row means "both limits unlimited", which is what
every deployment upgrading into this migration was doing a moment earlier.

Revision ID: 2e14e73b0442
Revises: f3a4b5c6d7e8
Create Date: 2026-08-26

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '2e14e73b0442'
down_revision: Union[str, None] = 'f3a4b5c6d7e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'instance_settings',
        sa.Column('id', sa.dialects.postgresql.UUID(), primary_key=True,
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('version', sa.BigInteger(), server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('created_by', sa.dialects.postgresql.UUID(),
                  sa.ForeignKey('user.id', ondelete='SET NULL', onupdate='RESTRICT')),
        sa.Column('updated_by', sa.dialects.postgresql.UUID(),
                  sa.ForeignKey('user.id', ondelete='SET NULL', onupdate='RESTRICT')),
        # Constant 1 + UNIQUE: "at most one row" as a database fact.
        sa.Column('singleton', sa.Integer(), nullable=False, server_default=sa.text('1')),
        sa.Column('max_workspace_users', sa.BigInteger()),
        sa.Column('max_concurrent_logins', sa.BigInteger()),
        sa.Column('login_idle_minutes', sa.Integer(), nullable=False,
                  server_default=sa.text('30')),
        sa.UniqueConstraint('singleton', name='instance_settings_singleton_key'),
        sa.CheckConstraint('singleton = 1', name='instance_settings_singleton_check'),
        sa.CheckConstraint('max_workspace_users IS NULL OR max_workspace_users >= 0',
                           name='instance_settings_workspace_users_check'),
        sa.CheckConstraint('max_concurrent_logins IS NULL OR max_concurrent_logins >= 0',
                           name='instance_settings_logins_check'),
        sa.CheckConstraint('login_idle_minutes >= 1',
                           name='instance_settings_idle_check'),
    )


def downgrade() -> None:
    op.drop_table('instance_settings')
