"""Add GDPR consent tables (policy_versions, user_consents)

Revision ID: dd2e3f4a5b6c
Revises: cc1d2e3f4a5b
Create Date: 2026-07-04 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'dd2e3f4a5b6c'
down_revision = 'cc1d2e3f4a5b'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'policy_versions',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('version', sa.Text(), nullable=False),
        sa.Column('languages', postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
        sa.Column('effective_from', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('content_hashes', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('policy_versions_version_idx', 'policy_versions', ['version'], unique=True)
    op.create_index('policy_versions_effective_from_idx', 'policy_versions', ['effective_from'])

    op.create_table(
        'user_consents',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(), nullable=False),
        sa.Column('policy_version', sa.Text(), nullable=False),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('withdrawn_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('purposes', postgresql.JSONB(), nullable=True),
        sa.Column('version', sa.BigInteger(), server_default=sa.text('0'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['policy_version'], ['policy_versions.version'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('user_consents_user_id_idx', 'user_consents', ['user_id'])
    # Partial unique index: at most one ACTIVE consent per (user, version).
    # Makes concurrent first-consent idempotent while allowing re-consent
    # after withdrawal (withdrawn rows stay for the audit trail).
    op.create_index(
        'user_consents_active_uq',
        'user_consents',
        ['user_id', 'policy_version'],
        unique=True,
        postgresql_where=sa.text('withdrawn_at IS NULL'),
    )


def downgrade():
    op.drop_index('user_consents_active_uq', table_name='user_consents')
    op.drop_index('user_consents_user_id_idx', table_name='user_consents')
    op.drop_table('user_consents')
    op.drop_index('policy_versions_effective_from_idx', table_name='policy_versions')
    op.drop_index('policy_versions_version_idx', table_name='policy_versions')
    op.drop_table('policy_versions')
