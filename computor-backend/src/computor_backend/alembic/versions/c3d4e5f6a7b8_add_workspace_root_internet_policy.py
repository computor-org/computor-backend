"""add root/internet policy to workspace template + course template settings

Root and internet stop being properties of the workspace images and become
policy. Two levels, ANDed inside the Terraform template so the weaker input
always wins:

- workspace_template_settings.allow_root / allow_internet — the CEILING,
  pushed as the Terraform variables of the same name at template push time.
  Defaults mirror the templates' own variable defaults (root off, internet
  on), so a template without a settings row behaves like one with a default
  row.
- course_workspace_template.allow_root / allow_internet — per-course
  narrowing, delivered as rich parameters at provision time. NULL means
  inherit the template; True cannot grant what the template denies.

Revision ID: c3d4e5f6a7b8
Revises: d8e9f0a1b2c3
Create Date: 2026-07-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'd8e9f0a1b2c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'workspace_template_settings',
        sa.Column('allow_root', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    )
    op.add_column(
        'workspace_template_settings',
        sa.Column('allow_internet', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    )
    # Nullable on purpose: NULL = inherit the template, which is not the same
    # statement as False (deny).
    op.add_column('course_workspace_template', sa.Column('allow_root', sa.Boolean(), nullable=True))
    op.add_column('course_workspace_template', sa.Column('allow_internet', sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column('course_workspace_template', 'allow_internet')
    op.drop_column('course_workspace_template', 'allow_root')
    op.drop_column('workspace_template_settings', 'allow_internet')
    op.drop_column('workspace_template_settings', 'allow_root')
