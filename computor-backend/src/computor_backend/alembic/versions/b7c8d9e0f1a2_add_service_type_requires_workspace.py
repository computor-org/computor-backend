"""add service_type.requires_workspace

Revision ID: b7c8d9e0f1a2
Revises: 6f1aef093aac
Create Date: 2026-04-23 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c8d9e0f1a2'
down_revision: Union[str, None] = '6f1aef093aac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add requires_workspace flag to service_type.

    Replaces the hardcoded ``path.startswith('agent')`` carve-out in the
    CourseMember post-create hook with a first-class boolean. When True,
    services of this type get workspace provisioning (GitLab repo fork,
    etc.) for their course members. When False, provisioning is skipped.

    Default is False so existing service types (including the seeded
    ``agent`` type) are treated as "no workspace needed" — which matches
    the observed/intended behavior for AI agent services.
    """
    op.add_column(
        'service_type',
        sa.Column(
            'requires_workspace',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        ),
    )


def downgrade() -> None:
    """Remove requires_workspace from service_type."""
    op.drop_column('service_type', 'requires_workspace')
