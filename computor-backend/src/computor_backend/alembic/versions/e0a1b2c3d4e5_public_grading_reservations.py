"""Durable, bounded admission for public student grading.

Revision ID: e0a1b2c3d4e5
Revises: d9e1f3a5b7c9
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e0a1b2c3d4e5"
down_revision = "d9e1f3a5b7c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "public_grading_reservation",
        sa.Column("workflow_id", sa.String(255), primary_key=True),
        sa.Column("result_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("released_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_public_grading_reservation_result_id",
                    "public_grading_reservation", ["result_id"])
    op.create_index("public_grading_reservation_open_idx",
                    "public_grading_reservation", ["created_at"],
                    postgresql_where=sa.text("released_at IS NULL"))


def downgrade() -> None:
    op.drop_index("public_grading_reservation_open_idx", table_name="public_grading_reservation")
    op.drop_index("ix_public_grading_reservation_result_id", table_name="public_grading_reservation")
    op.drop_table("public_grading_reservation")
