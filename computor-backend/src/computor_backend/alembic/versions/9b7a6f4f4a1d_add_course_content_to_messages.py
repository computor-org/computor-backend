"""add course_content target to messages

Revision ID: 9b7a6f4f4a1d
Revises: 6c2c37382ca7
Create Date: 2025-02-13 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '9b7a6f4f4a1d'
down_revision = '6c2c37382ca7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('message', sa.Column('course_content_id', postgresql.UUID(), nullable=True))
    op.add_column('message', sa.Column('course_id', postgresql.UUID(), nullable=True))
    op.create_index('msg_course_content_archived_idx', 'message', ['course_content_id', 'archived_at'])
    op.create_index('msg_course_archived_idx', 'message', ['course_id', 'archived_at'])
    op.create_foreign_key(
        'message_course_content_id_fkey',
        'message',
        'course_content',
        ['course_content_id'],
        ['id'],
        ondelete='CASCADE',
        onupdate='RESTRICT'
    )
    op.create_foreign_key(
        'message_course_id_fkey',
        'message',
        'course',
        ['course_id'],
        ['id'],
        ondelete='CASCADE',
        onupdate='RESTRICT'
    )


def downgrade() -> None:
    op.drop_constraint('message_course_id_fkey', 'message', type_='foreignkey')
    op.drop_constraint('message_course_content_id_fkey', 'message', type_='foreignkey')
    op.drop_index('msg_course_archived_idx', table_name='message')
    op.drop_index('msg_course_content_archived_idx', table_name='message')
    op.drop_column('message', 'course_id')
    op.drop_column('message', 'course_content_id')
