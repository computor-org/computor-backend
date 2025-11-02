"""rename testing_service_type_id to testing_service_id

Revision ID: 9e1f25901386
Revises: 1187444942f8
Create Date: 2025-10-29 12:37:52.913610

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9e1f25901386'
down_revision: Union[str, None] = '1187444942f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename testing_service_type_id to testing_service_id in course_content and result tables."""

    # Drop foreign key constraints first - try multiple possible constraint names
    # The constraint names may vary depending on how they were created
    op.execute("""
        DO $$
        BEGIN
            -- Drop course_content FK constraint (try both possible names)
            IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'course_content_testing_service_type_id_fkey') THEN
                ALTER TABLE course_content DROP CONSTRAINT course_content_testing_service_type_id_fkey;
            END IF;

            -- Drop result FK constraint (try multiple possible names)
            IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'result_testing_service_type_id_fkey') THEN
                ALTER TABLE result DROP CONSTRAINT result_testing_service_type_id_fkey;
            ELSIF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'result_testing_service_id_fkey') THEN
                ALTER TABLE result DROP CONSTRAINT result_testing_service_id_fkey;
            END IF;
        END $$;
    """)

    # Rename columns
    op.alter_column('course_content', 'testing_service_type_id', new_column_name='testing_service_id')
    op.alter_column('result', 'testing_service_type_id', new_column_name='testing_service_id')

    # Recreate foreign key constraints pointing to service table
    op.create_foreign_key(
        'course_content_testing_service_id_fkey',
        'course_content', 'service',
        ['testing_service_id'], ['id'],
        ondelete='RESTRICT'
    )
    op.create_foreign_key(
        'result_testing_service_id_fkey',
        'result', 'service',
        ['testing_service_id'], ['id'],
        ondelete='RESTRICT'
    )

    # Log the change
    op.execute("""
        DO $$
        BEGIN
            RAISE NOTICE 'Renamed testing_service_type_id to testing_service_id';
            RAISE NOTICE '  - course_content.testing_service_id now references service.id';
            RAISE NOTICE '  - result.testing_service_id now references service.id';
            RAISE NOTICE '  - Architecture: CourseContent → Service → ServiceType';
        END $$;
    """)


def downgrade() -> None:
    """Rollback: Rename testing_service_id back to testing_service_type_id."""

    # Drop foreign key constraints
    op.drop_constraint('course_content_testing_service_id_fkey', 'course_content', type_='foreignkey')
    op.drop_constraint('result_testing_service_id_fkey', 'result', type_='foreignkey')

    # Rename columns back
    op.alter_column('course_content', 'testing_service_id', new_column_name='testing_service_type_id')
    op.alter_column('result', 'testing_service_id', new_column_name='testing_service_type_id')

    # Recreate foreign key constraints pointing to service_type table
    op.create_foreign_key(
        'course_content_testing_service_type_id_fkey',
        'course_content', 'service_type',
        ['testing_service_type_id'], ['id'],
        ondelete='RESTRICT'
    )
    op.create_foreign_key(
        'result_testing_service_id_fkey',
        'result', 'service_type',
        ['testing_service_type_id'], ['id'],
        ondelete='RESTRICT'
    )
