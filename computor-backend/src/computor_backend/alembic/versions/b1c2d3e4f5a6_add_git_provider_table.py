"""add git_provider table and migrate tokens from organization properties

Revision ID: b1c2d3e4f5a6
Revises: a3b4c5d6e7f8
Create Date: 2026-05-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, None] = 'a3b4c5d6e7f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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

    # Migrate existing GitLab tokens out of organization.properties["gitlab"]
    op.execute("""
        INSERT INTO git_provider (organization_id, type, url, token)
        SELECT
            id,
            'gitlab',
            properties -> 'gitlab' ->> 'url',
            properties -> 'gitlab' ->> 'token'
        FROM organization
        WHERE
            properties -> 'gitlab' ->> 'url'   IS NOT NULL
            AND properties -> 'gitlab' ->> 'token' IS NOT NULL
            AND properties -> 'gitlab' ->> 'token' <> '';
    """)

    # Remove url and token from the JSONB — leave the rest (group_id, full_path, etc.)
    op.execute("""
        UPDATE organization
        SET properties = jsonb_set(
            properties,
            '{gitlab}',
            (properties -> 'gitlab') - 'token' - 'url'
        )
        WHERE properties -> 'gitlab' IS NOT NULL;
    """)


def downgrade() -> None:
    # Restore url and token back into organization.properties["gitlab"]
    op.execute("""
        UPDATE organization o
        SET properties = jsonb_set(
            jsonb_set(
                o.properties,
                '{gitlab, url}',
                to_jsonb(gp.url)
            ),
            '{gitlab, token}',
            to_jsonb(gp.token)
        )
        FROM git_provider gp
        WHERE gp.organization_id = o.id
          AND gp.type = 'gitlab';
    """)

    op.drop_index('ix_git_provider_organization_id', table_name='git_provider')
    op.drop_table('git_provider')
