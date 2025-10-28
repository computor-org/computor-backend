"""add_service_accounts_and_api_tokens

This migration adds:
1. Service table for service account metadata
2. ApiToken table for API token authentication with scopes
3. is_service flag to User table to distinguish service accounts
4. Migrates existing user_type='token' users to is_service=true

Revision ID: 19266bf266e9
Revises: d32f835b7227
Create Date: 2025-10-28 21:19:34.913627

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '19266bf266e9'
down_revision: Union[str, None] = 'd32f835b7227'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add service accounts and API token system."""

    # 1. Add is_service column to user table
    op.add_column('user', sa.Column('is_service', sa.Boolean(), server_default=sa.text('false'), nullable=False))

    # 2. Migrate existing 'token' type users to service users
    op.execute("""
        UPDATE "user"
        SET is_service = true
        WHERE user_type = 'token'
    """)

    # 3. Create Service table
    op.create_table('service',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('version', sa.BigInteger(), server_default=sa.text('0'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(), nullable=True),
        sa.Column('updated_by', postgresql.UUID(), nullable=True),
        sa.Column('properties', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('service_type', sa.String(length=63), nullable=False),
        sa.Column('user_id', postgresql.UUID(), nullable=False),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=True),
        sa.Column('enabled', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("slug ~* '^[a-z0-9][a-z0-9-]*[a-z0-9]$'", name='ck_service_slug_format'),
        sa.ForeignKeyConstraint(['created_by'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index('idx_service_enabled', 'service', ['enabled'], unique=False,
                    postgresql_where=sa.text("enabled = true AND archived_at IS NULL"))
    op.create_index('idx_service_type', 'service', ['service_type'], unique=False)

    # 4. Create ApiToken table
    op.create_table('api_token',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('version', sa.BigInteger(), server_default=sa.text('0'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(), nullable=True),
        sa.Column('updated_by', postgresql.UUID(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('user_id', postgresql.UUID(), nullable=False),
        sa.Column('token_hash', sa.LargeBinary(), nullable=False),
        sa.Column('token_prefix', sa.String(length=12), nullable=False),
        sa.Column('scopes', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('usage_count', sa.BigInteger(), server_default=sa.text('0'), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revocation_reason', sa.Text(), nullable=True),
        sa.Column('properties', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.CheckConstraint('(expires_at IS NULL) OR (expires_at > created_at)', name='ck_api_token_expiration'),
        sa.ForeignKeyConstraint(['created_by'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash')
    )
    op.create_index('idx_api_token_hash_active', 'api_token', ['token_hash'], unique=False,
                    postgresql_where=sa.text('revoked_at IS NULL'))
    op.create_index('idx_api_token_prefix', 'api_token', ['token_prefix'], unique=False)
    op.create_index('idx_api_token_user_active', 'api_token', ['user_id'], unique=False,
                    postgresql_where=sa.text('revoked_at IS NULL'))
    op.create_index(op.f('ix_api_token_user_id'), 'api_token', ['user_id'], unique=False)

    # 5. Create index for service users
    op.create_index('idx_user_service', 'user', ['is_service'], unique=False,
                    postgresql_where=sa.text('is_service = true'))


def downgrade() -> None:
    """Downgrade schema - remove service accounts and API token system."""

    # Drop indexes
    op.drop_index('idx_user_service', table_name='user', postgresql_where=sa.text('is_service = true'))
    op.drop_index(op.f('ix_api_token_user_id'), table_name='api_token')
    op.drop_index('idx_api_token_user_active', table_name='api_token', postgresql_where=sa.text('revoked_at IS NULL'))
    op.drop_index('idx_api_token_prefix', table_name='api_token')
    op.drop_index('idx_api_token_hash_active', table_name='api_token', postgresql_where=sa.text('revoked_at IS NULL'))
    op.drop_index('idx_service_type', table_name='service')
    op.drop_index('idx_service_enabled', table_name='service', postgresql_where=sa.text("enabled = true AND archived_at IS NULL"))

    # Drop tables
    op.drop_table('api_token')
    op.drop_table('service')

    # Remove is_service column
    op.drop_column('user', 'is_service')
