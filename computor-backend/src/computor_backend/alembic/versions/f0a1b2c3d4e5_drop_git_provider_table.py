"""drop the organization-scoped git_provider table

Removes the legacy organization-scoped ``git_provider`` table (added by
b1c2d3e4f5a6). Git is now per-course: courses bind to a ``git_server`` from the
global GitServer registry via ``course_git_binding`` — organizations no longer
carry a git connection. Nothing reads ``git_provider`` anymore.

No data translation: existing rows are dropped. Per-course git is (re)configured
through the GitServer registry + course bindings.

Revision ID: f0a1b2c3d4e5
Revises: e6f7a8b9c0d1
Create Date: 2026-07-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'f0a1b2c3d4e5'
down_revision: Union[str, None] = 'e6f7a8b9c0d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the organization-scoped git_provider table."""
    op.drop_index('ix_git_provider_organization_id', table_name='git_provider')
    op.drop_table('git_provider')


def downgrade() -> None:
    """Recreate the git_provider table (structure only; no data restored)."""
    op.create_table(
        'git_provider',
        sa.Column('id', UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('version', sa.BigInteger(), server_default=sa.text('0'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', UUID(), nullable=True),
        sa.Column('updated_by', UUID(), nullable=True),
        sa.Column('organization_id', UUID(), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('url', sa.String(2048), nullable=False),
        sa.Column('token', sa.String(4096), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_id'], ['organization.id'], ondelete='CASCADE', onupdate='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_git_provider_organization_id', 'git_provider', ['organization_id'])
