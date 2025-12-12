"""add_organization_course_family_to_message

Revision ID: eb65f8f584b6
Revises: 83eab3cc737f
Create Date: 2025-12-10 12:50:04.628292

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'eb65f8f584b6'
down_revision: Union[str, None] = '83eab3cc737f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Adds organization_id and course_family_id columns to the message table
    to support organization-level and course family-level messaging scopes.
    """
    # Add new columns for organization and course_family message targets
    op.add_column('message', sa.Column('organization_id', postgresql.UUID(), nullable=True))
    op.add_column('message', sa.Column('course_family_id', postgresql.UUID(), nullable=True))

    # Create indexes for efficient querying
    op.create_index('msg_organization_archived_idx', 'message', ['organization_id', 'archived_at'], unique=False)
    op.create_index('msg_course_family_archived_idx', 'message', ['course_family_id', 'archived_at'], unique=False)

    # Create foreign key constraints
    op.create_foreign_key(
        'fk_message_organization_id',
        'message', 'organization',
        ['organization_id'], ['id'],
        onupdate='RESTRICT', ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_message_course_family_id',
        'message', 'course_family',
        ['course_family_id'], ['id'],
        onupdate='RESTRICT', ondelete='CASCADE'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop foreign key constraints
    op.drop_constraint('fk_message_course_family_id', 'message', type_='foreignkey')
    op.drop_constraint('fk_message_organization_id', 'message', type_='foreignkey')

    # Drop indexes
    op.drop_index('msg_course_family_archived_idx', table_name='message')
    op.drop_index('msg_organization_archived_idx', table_name='message')

    # Drop columns
    op.drop_column('message', 'course_family_id')
    op.drop_column('message', 'organization_id')
