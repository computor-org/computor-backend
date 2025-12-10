"""add_default_agent_service_type

Revision ID: 83eab3cc737f
Revises: 4327038d4ae3
Create Date: 2025-12-05 23:38:32.072430

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '83eab3cc737f'
down_revision: Union[str, None] = '4327038d4ae3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Insert default agent ServiceType
    op.execute("""
        INSERT INTO service_type (path, name, description, category, schema, properties)
        VALUES (
            'agent',
            'AI Agent',
            'Service type for AI agents that assist with course-related tasks',
            'agent',
            '{"type": "object", "properties": {"model": {"type": "string", "description": "AI model identifier"}, "capabilities": {"type": "array", "items": {"type": "string"}, "description": "List of agent capabilities"}}, "required": []}'::jsonb,
            '{}'::jsonb
        )
        ON CONFLICT (path) DO NOTHING;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove the default agent ServiceType
    op.execute("""
        DELETE FROM service_type WHERE path = 'agent';
    """)
