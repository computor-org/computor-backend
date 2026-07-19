"""add workspace_template_settings

Per-Coder-template knobs Computor owns: container resource caps
(memory_mb / cpu_shares, pushed as Terraform --variable values at template
push time), the max_running_workspaces quota enforced at provision/start,
and extra Terraform variable overrides. Keyed by the Coder template name so
a row survives template re-pushes and the .computor-managed file re-sync.

Revision ID: b9c8d7e6f5a4
Revises: e1f2a3b4c5d6
Create Date: 2026-07-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'b9c8d7e6f5a4'
down_revision: Union[str, None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'workspace_template_settings',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('version', sa.BigInteger(), server_default=sa.text('0'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(), nullable=True),
        sa.Column('updated_by', postgresql.UUID(), nullable=True),
        sa.Column('template_name', sa.String(255), nullable=False),
        sa.Column('memory_mb', sa.BigInteger(), nullable=True),
        sa.Column('cpu_shares', sa.BigInteger(), nullable=True),
        sa.Column('max_running_workspaces', sa.BigInteger(), nullable=True),
        sa.Column('template_variables', postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('template_name', name='workspace_template_settings_name_key'),
        sa.CheckConstraint('memory_mb IS NULL OR memory_mb >= 0',
                           name='workspace_template_settings_memory_check'),
        sa.CheckConstraint('cpu_shares IS NULL OR cpu_shares >= 0',
                           name='workspace_template_settings_cpu_check'),
        sa.CheckConstraint('max_running_workspaces IS NULL OR max_running_workspaces >= 0',
                           name='workspace_template_settings_quota_check'),
    )


def downgrade() -> None:
    op.drop_table('workspace_template_settings')
