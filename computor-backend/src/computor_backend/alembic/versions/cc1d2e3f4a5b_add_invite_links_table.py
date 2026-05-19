"""Add invite_link table

Revision ID: cc1d2e3f4a5b
Revises: d5e6f7a8b9c0
Create Date: 2026-05-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'cc1d2e3f4a5b'
down_revision = 'd5e6f7a8b9c0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'invite_link',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('version', sa.BigInteger(), server_default=sa.text('0'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(), nullable=True),
        sa.Column('token', sa.String(64), nullable=False),
        sa.Column('email', sa.String(320), nullable=True),
        sa.Column('max_uses', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.Column('use_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('roles', postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('invite_link_token_idx', 'invite_link', ['token'], unique=True)
    op.create_index('invite_link_created_by_idx', 'invite_link', ['created_by'])


def downgrade():
    op.drop_index('invite_link_created_by_idx', table_name='invite_link')
    op.drop_index('invite_link_token_idx', table_name='invite_link')
    op.drop_table('invite_link')
