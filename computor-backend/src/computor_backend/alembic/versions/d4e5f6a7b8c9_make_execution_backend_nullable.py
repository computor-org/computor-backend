"""Allow null execution_backend_id on results

Revision ID: d4e5f6a7b8c9
Revises: c3d2e1f4b5a6
Create Date: 2025-05-18 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "d4e5f6a7b8c9"
down_revision = "c3d2e1f4b5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "result",
        "execution_backend_id",
        existing_type=postgresql.UUID(),
        nullable=True,
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE result AS r
        SET execution_backend_id = cc.execution_backend_id
        FROM course_content AS cc
        WHERE r.course_content_id = cc.id
          AND r.execution_backend_id IS NULL
        """
    )

    op.alter_column(
        "result",
        "execution_backend_id",
        existing_type=postgresql.UUID(),
        nullable=False,
    )

