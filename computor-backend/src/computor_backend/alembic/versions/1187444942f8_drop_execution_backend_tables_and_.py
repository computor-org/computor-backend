"""drop execution_backend tables and legacy columns

Revision ID: 1187444942f8
Revises: 43bcae6ff4a3
Create Date: 2025-10-29 12:11:03.388334

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '1187444942f8'
down_revision: Union[str, None] = '43bcae6ff4a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - remove legacy execution_backend tables and columns."""

    # Drop foreign keys first
    op.drop_constraint('course_content_execution_backend_id_fkey', 'course_content', type_='foreignkey')
    op.drop_constraint('result_execution_backend_id_fkey', 'result', type_='foreignkey')

    # Drop index on service.service_type if it exists
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_service_type') THEN
                DROP INDEX idx_service_type;
            END IF;
        END $$;
    """)

    # Drop legacy columns from tables
    op.drop_column('course_content', 'execution_backend_id')
    op.drop_column('result', 'execution_backend_id')
    op.drop_column('service', 'service_type')

    # Drop index from result table if it exists (contains execution_backend_id)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'result_commit_test_system_key') THEN
                DROP INDEX result_commit_test_system_key;
            END IF;
        END $$;
    """)

    # Drop old tables
    op.drop_table('course_execution_backend')
    op.drop_table('execution_backend')

    # Log completion
    op.execute("""
        DO $$
        BEGIN
            RAISE NOTICE 'Dropped legacy execution_backend tables and columns';
            RAISE NOTICE '  - Dropped course_execution_backend table';
            RAISE NOTICE '  - Dropped execution_backend table';
            RAISE NOTICE '  - Removed execution_backend_id from course_content';
            RAISE NOTICE '  - Removed execution_backend_id from result';
            RAISE NOTICE '  - Removed service_type string field from service';
        END $$;
    """)


def downgrade() -> None:
    """Downgrade schema - recreate execution_backend tables and columns."""

    # Recreate execution_backend table
    op.create_table(
        'execution_backend',
        sa.Column('id', postgresql.UUID(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column('version', sa.BigInteger(), server_default=sa.text("0"), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(), nullable=True),
        sa.Column('updated_by', postgresql.UUID(), nullable=True),
        sa.Column('properties', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('type', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.CheckConstraint("(slug)::text ~* '^[A-Za-z0-9_-]+$'::text"),
        sa.ForeignKeyConstraint(['created_by'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )

    # Recreate course_execution_backend table
    op.create_table(
        'course_execution_backend',
        sa.Column('execution_backend_id', postgresql.UUID(), nullable=False),
        sa.Column('course_id', postgresql.UUID(), nullable=False),
        sa.Column('version', sa.BigInteger(), server_default=sa.text("0"), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(), nullable=True),
        sa.Column('updated_by', postgresql.UUID(), nullable=True),
        sa.Column('properties', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['course_id'], ['course.id'], ondelete='CASCADE', onupdate='RESTRICT'),
        sa.ForeignKeyConstraint(['execution_backend_id'], ['execution_backend.id'], ondelete='CASCADE', onupdate='RESTRICT'),
        sa.PrimaryKeyConstraint('execution_backend_id', 'course_id')
    )

    # Recreate columns
    op.add_column('course_content', sa.Column('execution_backend_id', postgresql.UUID(), nullable=True))
    op.add_column('result', sa.Column('execution_backend_id', postgresql.UUID(), nullable=True))
    op.add_column('service', sa.Column('service_type', sa.String(length=63), nullable=True))

    # Recreate foreign keys
    op.create_foreign_key('course_content_execution_backend_id_fkey', 'course_content', 'execution_backend', ['execution_backend_id'], ['id'], ondelete='CASCADE', onupdate='RESTRICT')
    op.create_foreign_key('result_execution_backend_id_fkey', 'result', 'execution_backend', ['execution_backend_id'], ['id'], ondelete='RESTRICT', onupdate='RESTRICT')

    # Recreate index
    op.create_index('result_commit_test_system_key', 'result', ['test_system_id', 'execution_backend_id'], unique=True)
