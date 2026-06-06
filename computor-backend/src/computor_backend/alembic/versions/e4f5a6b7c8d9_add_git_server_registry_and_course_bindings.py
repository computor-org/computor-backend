"""add git_server registry, course_git_binding and course_member_repository

Course-level git: move the git binding from the organization to the course.
Adds a registry of git server instances, a per-course binding to one of them
(with the student-template location + allowed student-repo modes), and a
per-student repository tracking record. See COURSE_LEVEL_GIT_REFACTOR.md.

Schema only — no data is migrated here. Converting the legacy org-scoped
``git_provider`` rows + ``course.properties.gitlab`` into these tables is done
by a separate, idempotent, dry-run-able external script.

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-06-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'e4f5a6b7c8d9'
down_revision: Union[str, None] = 'd3e4f5a6b7c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- git server registry -------------------------------------------------
    op.create_table(
        'git_server',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('version', sa.BigInteger(), server_default=sa.text('0'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(), nullable=True),
        sa.Column('updated_by', postgresql.UUID(), nullable=True),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('base_url', sa.String(2048), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('managed', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('token', sa.String(4096), nullable=True),
        sa.Column('properties', postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('type', 'base_url', name='git_server_type_url_key'),
        sa.CheckConstraint("type IN ('forgejo', 'gitlab')", name='git_server_type_check'),
    )

    # --- per-course binding (1:1) --------------------------------------------
    op.create_table(
        'course_git_binding',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('version', sa.BigInteger(), server_default=sa.text('0'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(), nullable=True),
        sa.Column('updated_by', postgresql.UUID(), nullable=True),
        sa.Column('course_id', postgresql.UUID(), nullable=False),
        sa.Column('delivery', sa.String(50), server_default=sa.text("'git'"), nullable=False),
        sa.Column('git_server_id', postgresql.UUID(), nullable=True),
        sa.Column('template_repo', sa.String(2048), nullable=True),
        sa.Column('template_url', sa.String(2048), nullable=True),
        sa.Column('default_branch', sa.String(255), server_default=sa.text("'main'"), nullable=True),
        sa.Column('student_repo_modes', postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column('properties', postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['course_id'], ['course.id'], ondelete='CASCADE', onupdate='RESTRICT'),
        sa.ForeignKeyConstraint(['git_server_id'], ['git_server.id'], ondelete='RESTRICT', onupdate='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('course_id', name='course_git_binding_course_key'),
        sa.CheckConstraint("delivery IN ('git', 'download')", name='course_git_binding_delivery_check'),
    )

    # --- per-student repository tracking record (1:1 with course_member) ------
    op.create_table(
        'course_member_repository',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('version', sa.BigInteger(), server_default=sa.text('0'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(), nullable=True),
        sa.Column('updated_by', postgresql.UUID(), nullable=True),
        sa.Column('course_member_id', postgresql.UUID(), nullable=False),
        sa.Column('mode', sa.String(50), nullable=False),
        sa.Column('git_server_id', postgresql.UUID(), nullable=True),
        sa.Column('server_url', sa.String(2048), nullable=True),
        sa.Column('repo_ref', sa.String(2048), nullable=True),
        sa.Column('http_url', sa.String(2048), nullable=True),
        sa.Column('ssh_url', sa.String(2048), nullable=True),
        sa.Column('web_url', sa.String(2048), nullable=True),
        sa.Column('properties', postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['course_member_id'], ['course_member.id'], ondelete='CASCADE', onupdate='RESTRICT'),
        sa.ForeignKeyConstraint(['git_server_id'], ['git_server.id'], ondelete='SET NULL', onupdate='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('course_member_id', name='course_member_repository_member_key'),
        sa.CheckConstraint(
            "mode IN ('forgejo', 'gitlab_byo', 'download')",
            name='course_member_repository_mode_check',
        ),
    )


def downgrade() -> None:
    op.drop_table('course_member_repository')
    op.drop_table('course_git_binding')
    op.drop_table('git_server')
