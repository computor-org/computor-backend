"""remove_deprecated_example_version_id_from_course_content

Revision ID: 059601a6c7ef
Revises: add_sg_cascade_002
Create Date: 2025-10-16 19:50:24.553822

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '059601a6c7ef'
down_revision: Union[str, None] = 'add_sg_cascade_002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Remove deprecated example_version_id column from course_content table.

    This column is deprecated and replaced by CourseContentDeployment.example_version_id.
    All example assignments should now be tracked through the CourseContentDeployment table.
    """
    # Data migration: Fix any existing NULL deployment_path values
    # Set deployment_path to example_identifier for existing deployments that don't have it set
    op.execute("""
        UPDATE course_content_deployment
        SET deployment_path = example_identifier::text
        WHERE deployment_path IS NULL
          AND example_identifier IS NOT NULL
    """)

    # Drop the trigger that validates example assignments on course_content
    # (This validation now happens through CourseContentDeployment business logic)
    op.execute("DROP TRIGGER IF EXISTS trg_validate_course_content_example ON course_content CASCADE")

    # Drop the trigger function
    op.execute("DROP FUNCTION IF EXISTS validate_course_content_example_submittable() CASCADE")

    # Drop the foreign key constraint
    op.drop_constraint('course_content_example_version_id_fkey', 'course_content', type_='foreignkey')

    # Drop the deprecated column
    op.drop_column('course_content', 'example_version_id')


def downgrade() -> None:
    """
    Re-add the deprecated example_version_id column.

    Note: This column will be empty after downgrade - it was deprecated and
    the data should be in CourseContentDeployment instead.
    """
    # Add the column back
    op.add_column('course_content', sa.Column('example_version_id', sa.UUID(), nullable=True))

    # Re-create the foreign key constraint
    op.create_foreign_key(
        'course_content_example_version_id_fkey',
        'course_content',
        'example_version',
        ['example_version_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # Re-create the trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION validate_course_content_example_submittable()
        RETURNS TRIGGER AS $$
        DECLARE
            is_submittable boolean;
        BEGIN
            -- Skip if no example is set
            IF NEW.example_version_id IS NULL THEN
                RETURN NEW;
            END IF;

            -- Check if the content type's kind is submittable
            SELECT cck.submittable INTO is_submittable
            FROM course_content_type cct
            JOIN course_content_kind cck ON cct.course_content_kind_id = cck.id
            WHERE cct.id = NEW.course_content_type_id;

            IF NOT is_submittable THEN
                RAISE EXCEPTION 'Only submittable content can have examples';
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Re-create the trigger
    op.execute("""
        CREATE TRIGGER trg_validate_course_content_example
        BEFORE INSERT OR UPDATE OF example_version_id ON course_content
        FOR EACH ROW
        EXECUTE FUNCTION validate_course_content_example_submittable();
    """)
