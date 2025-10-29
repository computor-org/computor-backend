"""add_default_testing_temporal_service_type

Revision ID: 70413c285ac5
Revises: 9e1f25901386
Create Date: 2025-10-29 14:27:17.511582

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '70413c285ac5'
down_revision: Union[str, None] = '9e1f25901386'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Insert default testing.temporal ServiceType
    op.execute("""
        INSERT INTO service_type (path, name, description, category, schema, properties)
        VALUES (
            'testing.temporal',
            'Temporal Testing Worker',
            'Service type for temporal workers that execute student code tests',
            'testing',
            '{"type": "object", "properties": {"language": {"type": "string", "enum": ["python", "matlab", "java", "cpp"]}}, "required": ["language"]}'::jsonb,
            '{"task_queue": "computor-tasks", "async": true}'::jsonb
        )
        ON CONFLICT (path) DO NOTHING;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove the default testing.temporal ServiceType
    op.execute("""
        DELETE FROM service_type WHERE path = 'testing.temporal';
    """)
