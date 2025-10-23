"""add cascade to submission_group foreign key

Revision ID: add_sg_cascade_002
Revises: 32b313efe198
Create Date: 2025-10-09

This migration updates the submission_group.course_content_id foreign key
to have ON DELETE CASCADE, allowing proper cleanup when course content is deleted.

Business logic validation (in crud.py) ensures:
1. Cannot delete course_content if submissions exist
2. Deleting parent course_content cascades to descendants via Ltree
3. Database CASCADE handles submission_groups cleanup automatically
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_sg_cascade_002'
down_revision = '32b313efe198'
branch_labels = None
depends_on = None


def upgrade():
    # Drop the existing foreign key constraint
    op.drop_constraint(
        'submission_group_course_content_id_fkey',
        'submission_group',
        type_='foreignkey'
    )

    # Recreate it with ON DELETE CASCADE
    op.create_foreign_key(
        'submission_group_course_content_id_fkey',
        'submission_group',
        'course_content',
        ['course_content_id'],
        ['id'],
        ondelete='CASCADE',
        onupdate='RESTRICT'
    )


def downgrade():
    # Drop the CASCADE foreign key
    op.drop_constraint(
        'submission_group_course_content_id_fkey',
        'submission_group',
        type_='foreignkey'
    )

    # Recreate it without CASCADE (original state)
    op.create_foreign_key(
        'submission_group_course_content_id_fkey',
        'submission_group',
        'course_content',
        ['course_content_id'],
        ['id'],
        onupdate='RESTRICT'
    )
