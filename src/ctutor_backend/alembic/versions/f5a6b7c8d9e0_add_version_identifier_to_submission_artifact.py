"""Add version_identifier to submission_artifact

Revision ID: f5a6b7c8d9e0
Revises: e8b1f4c3d2a0
Create Date: 2024-01-29 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f5a6b7c8d9e0'
down_revision = 'e8b1f4c3d2a0'
branch_labels = None
depends_on = None


def upgrade():
    # Add version_identifier column to submission_artifact table
    op.add_column('submission_artifact',
        sa.Column('version_identifier', sa.String(length=255), nullable=True)
    )

    # Create index on version_identifier for faster queries
    op.create_index('submission_artifact_version_idx',
                     'submission_artifact',
                     ['version_identifier'],
                     unique=False)

    # Migrate existing data from properties JSONB to the new column
    # This will extract version_identifier from properties if it exists
    op.execute("""
        UPDATE submission_artifact
        SET version_identifier = properties->>'version_identifier'
        WHERE properties ? 'version_identifier'
    """)

    # Remove version_identifier from properties JSONB to avoid duplication
    op.execute("""
        UPDATE submission_artifact
        SET properties = properties - 'version_identifier'
        WHERE properties ? 'version_identifier'
    """)


def downgrade():
    # Move version_identifier back to properties before removing column
    op.execute("""
        UPDATE submission_artifact
        SET properties = COALESCE(properties, '{}'::jsonb) ||
                        jsonb_build_object('version_identifier', version_identifier)
        WHERE version_identifier IS NOT NULL
    """)

    # Drop the index
    op.drop_index('submission_artifact_version_idx', table_name='submission_artifact')

    # Drop the column
    op.drop_column('submission_artifact', 'version_identifier')