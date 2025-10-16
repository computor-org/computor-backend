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
    # Drop the foreign key constraint first
    op.drop_constraint('course_content_example_version_id_fkey', 'course_content', type_='foreignkey')

    # Drop the column
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
