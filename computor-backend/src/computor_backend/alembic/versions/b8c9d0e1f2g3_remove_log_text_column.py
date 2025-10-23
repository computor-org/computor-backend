"""remove_log_text_column

Revision ID: b8c9d0e1f2g3
Revises: a7b8c9d0e1f2
Create Date: 2025-10-18 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8c9d0e1f2g3'
down_revision: Union[str, None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Remove log_text column from result table.

    The log_text field was used to store test execution logs in the database,
    but was never exposed via API or displayed to users. Going forward, all
    logging should use the application logger instead of database storage.

    Note: Existing log_text data is NOT migrated. This is intentional as
    the data was never used/displayed.
    """
    # Drop the log_text column from result table
    op.drop_column('result', 'log_text')


def downgrade() -> None:
    """
    Restore log_text column to database.

    Note: This will recreate the column but historical data will be lost.
    """
    # Re-add the log_text column
    op.add_column('result', sa.Column('log_text', sa.String(), nullable=True))
