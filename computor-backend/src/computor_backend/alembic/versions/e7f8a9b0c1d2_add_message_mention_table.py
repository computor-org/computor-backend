"""add message_mention table

Revision ID: e7f8a9b0c1d2
Revises: a7f3b1c9d2e8
Create Date: 2026-06-26

Adds the message <-> mentioned-user relation that backs @mentions. Rows are
created from the ``@[name](user_id)`` tokens in ``Message.content`` once the
mentioned user is confirmed to be in the message's audience.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e7f8a9b0c1d2'
down_revision: Union[str, None] = 'a7f3b1c9d2e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'message_mention',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('message_id', postgresql.UUID(), nullable=False),
        sa.Column('mentioned_user_id', postgresql.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['message_id'], ['message.id'], onupdate='RESTRICT', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['mentioned_user_id'], ['user.id'], onupdate='RESTRICT', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    # One row per (message, user).
    op.create_index('msg_mention_unique_idx', 'message_mention', ['message_id', 'mentioned_user_id'], unique=True)
    # "Messages that mention me" fast path.
    op.create_index('msg_mention_user_idx', 'message_mention', ['mentioned_user_id', 'message_id'], unique=False)


def downgrade() -> None:
    op.drop_index('msg_mention_user_idx', table_name='message_mention')
    op.drop_index('msg_mention_unique_idx', table_name='message_mention')
    op.drop_table('message_mention')
