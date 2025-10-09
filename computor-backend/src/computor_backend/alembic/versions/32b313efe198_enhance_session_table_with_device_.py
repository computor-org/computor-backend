"""enhance session table with device tracking and token hashing

Revision ID: 32b313efe198
Revises: d4bce99cc44f
Create Date: 2025-10-09 20:06:09.377340

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '32b313efe198'
down_revision: Union[str, None] = 'd4bce99cc44f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    from sqlalchemy.dialects import postgresql

    # Add new columns to session table
    op.add_column('session', sa.Column('sid', postgresql.UUID(), server_default=sa.text("uuid_generate_v4()"), nullable=False))
    op.add_column('session', sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('session', sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('session', sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('session', sa.Column('revocation_reason', sa.String(255), nullable=True))
    op.add_column('session', sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('session', sa.Column('refresh_token_hash', sa.LargeBinary(), nullable=True))
    op.add_column('session', sa.Column('refresh_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('session', sa.Column('refresh_counter', sa.Integer(), server_default=sa.text("0"), nullable=False))
    op.add_column('session', sa.Column('last_ip', postgresql.INET(), nullable=True))
    op.add_column('session', sa.Column('user_agent', sa.Text(), nullable=True))
    op.add_column('session', sa.Column('device_label', sa.Text(), nullable=True))

    # Rename columns for clarity
    op.alter_column('session', 'ip_address', new_column_name='created_ip')

    # Ensure properties has default value
    op.execute("UPDATE session SET properties = '{}'::jsonb WHERE properties IS NULL")

    # Add unique constraint on sid
    op.create_unique_constraint('uq_session_sid', 'session', ['sid'])

    # Add partial index for active sessions
    op.execute("""
        CREATE INDEX ix_session_user_active ON session(user_id)
        WHERE revoked_at IS NULL AND ended_at IS NULL
        AND (expires_at IS NULL OR expires_at > now())
    """)

    # Add index on last_seen_at for activity tracking
    op.create_index('ix_session_last_seen', 'session', ['last_seen_at'])

    # Create trigger function for auto-updating updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION set_session_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
          NEW.updated_at = now();
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger
    op.execute("""
        DROP TRIGGER IF EXISTS trg_session_updated_at ON session;
        CREATE TRIGGER trg_session_updated_at
        BEFORE UPDATE ON session
        FOR EACH ROW EXECUTE PROCEDURE set_session_updated_at();
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop trigger and function
    op.execute("DROP TRIGGER IF EXISTS trg_session_updated_at ON session")
    op.execute("DROP FUNCTION IF EXISTS set_session_updated_at()")

    # Drop indexes
    op.drop_index('ix_session_last_seen', 'session')
    op.execute("DROP INDEX IF EXISTS ix_session_user_active")

    # Drop unique constraint
    op.drop_constraint('uq_session_sid', 'session', type_='unique')

    # Restore column name
    op.alter_column('session', 'created_ip', new_column_name='ip_address')

    # Drop new columns
    op.drop_column('session', 'device_label')
    op.drop_column('session', 'user_agent')
    op.drop_column('session', 'last_ip')
    op.drop_column('session', 'refresh_counter')
    op.drop_column('session', 'refresh_expires_at')
    op.drop_column('session', 'refresh_token_hash')
    op.drop_column('session', 'ended_at')
    op.drop_column('session', 'revocation_reason')
    op.drop_column('session', 'revoked_at')
    op.drop_column('session', 'expires_at')
    op.drop_column('session', 'last_seen_at')
    op.drop_column('session', 'sid')
