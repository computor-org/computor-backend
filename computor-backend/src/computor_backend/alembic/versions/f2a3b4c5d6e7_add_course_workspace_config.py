"""add course workspace config

Three additions for course-scoped workspaces:

- ``workspace_template_settings.enabled``: global per-template on/off switch
  (disabled templates are hidden from non-manager listings and cannot be
  provisioned by non-managers; existing workspaces keep starting).
- ``course_workspace_template``: join table of templates allowed in a course,
  granting course members course-derived workspace access without a global
  workspace role. template_name is deliberately not an FK to
  workspace_template_settings (settings rows are lazily upserted).
- ``course_workspace_settings``: course-wide flags, currently
  ``lecturer_provision_enabled`` (lecturers may bulk-provision throwaway
  workspaces for students).

Revision ID: f2a3b4c5d6e7
Revises: b9c8d7e6f5a4
Create Date: 2026-07-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'f2a3b4c5d6e7'
down_revision: Union[str, None] = 'b9c8d7e6f5a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'workspace_template_settings',
        sa.Column('enabled', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    )
    op.create_table(
        'course_workspace_template',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('version', sa.BigInteger(), server_default=sa.text('0'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(), nullable=True),
        sa.Column('updated_by', postgresql.UUID(), nullable=True),
        sa.Column('course_id', postgresql.UUID(), nullable=False),
        sa.Column('template_name', sa.String(255), nullable=False),
        sa.ForeignKeyConstraint(['course_id'], ['course.id'], ondelete='CASCADE', onupdate='RESTRICT'),
        sa.ForeignKeyConstraint(['created_by'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('course_id', 'template_name', name='course_workspace_template_key'),
    )
    op.create_table(
        'course_workspace_settings',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('version', sa.BigInteger(), server_default=sa.text('0'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(), nullable=True),
        sa.Column('updated_by', postgresql.UUID(), nullable=True),
        sa.Column('course_id', postgresql.UUID(), nullable=False),
        sa.Column('lecturer_provision_enabled', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.ForeignKeyConstraint(['course_id'], ['course.id'], ondelete='CASCADE', onupdate='RESTRICT'),
        sa.ForeignKeyConstraint(['created_by'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('course_id', name='course_workspace_settings_course_key'),
    )


def downgrade() -> None:
    op.drop_table('course_workspace_settings')
    op.drop_table('course_workspace_template')
    op.drop_column('workspace_template_settings', 'enabled')
