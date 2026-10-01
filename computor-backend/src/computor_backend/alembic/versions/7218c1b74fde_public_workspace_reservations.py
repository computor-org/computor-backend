"""Durable reservations for public hosted workspace admission.

Revision ID: 7218c1b74fde
Revises: e0a1b2c3d4e5
Create Date: 2026-10-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7218c1b74fde"
down_revision: str | None = "e0a1b2c3d4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "public_workspace_reservation",
        sa.Column("owner_name", sa.Text(), nullable=False),
        sa.Column("workspace_name", sa.Text(), nullable=False),
        sa.Column("baseline_build_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("owner_name", "workspace_name"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT count(*) FROM public_workspace_reservation")).scalar():
        raise RuntimeError("Refusing to drop outstanding public workspace reservations")
    op.drop_table("public_workspace_reservation")
