"""Create tables for VS Code extension registry

Revision ID: e8b1f4c3d2a0
Revises: d4e5f6a7b8c9
Create Date: 2025-06-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as sa_pg


# revision identifiers, used by Alembic.
revision = "e8b1f4c3d2a0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "extension",
        sa.Column(
            "id",
            sa_pg.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("publisher", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("publisher", "name", name="uq_extension_identity"),
    )

    op.create_index(
        "ix_extension_identity",
        "extension",
        ["publisher", "name"],
        unique=False,
    )

    op.create_table(
        "extension_version",
        sa.Column(
            "id",
            sa_pg.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("extension_id", sa_pg.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("prerelease", sa.String(length=100), nullable=True),
        sa.Column("engine_range", sa.String(length=50), nullable=True),
        sa.Column(
            "yanked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "content_type",
            sa.String(length=100),
            nullable=False,
            server_default="application/octet-stream",
        ),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint([
            "extension_id"
        ], ["extension.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "extension_id",
            "version",
            name="uq_extension_version",
        ),
        sa.UniqueConstraint(
            "extension_id",
            "version_number",
            name="uq_extension_version_number",
        ),
    )

    op.create_index(
        "ix_extension_version_order",
        "extension_version",
        ["extension_id", "published_at", "version_number"],
        unique=False,
    )

    op.create_index(
        "ix_extension_version_sha256",
        "extension_version",
        ["sha256"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_extension_version_sha256", table_name="extension_version")
    op.drop_index("ix_extension_version_order", table_name="extension_version")
    op.drop_table("extension_version")

    op.drop_index("ix_extension_identity", table_name="extension")
    op.drop_table("extension")
