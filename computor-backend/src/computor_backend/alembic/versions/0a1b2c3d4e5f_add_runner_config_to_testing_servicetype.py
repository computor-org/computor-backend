"""extend testing.temporal ServiceType.schema with runner config

Revision ID: 0a1b2c3d4e5f
Revises: e0f1a2b3c4d5
Create Date: 2026-05-03 16:30:00.000000

"""
import json
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '0a1b2c3d4e5f'
down_revision: Union[str, None] = 'e0f1a2b3c4d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Mirrors ``ServiceRunnerConfig`` in ``computor-types/services.py``. The
# Pydantic class is the source of truth at write time; this snapshot is
# used by the API/UI to validate ``Service.config`` against the schema
# stored on ``service_type``.
_RUNNER_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "backend": {
            "type": "string",
            "enum": ["local", "docker"],
            "default": "local",
        },
        "docker_image": {"type": ["string", "null"]},
        "timeout_seconds": {"type": ["number", "null"], "exclusiveMinimum": 0},
        "memory_mb": {"type": ["integer", "null"], "exclusiveMinimum": 0},
        "cpus": {"type": ["number", "null"], "exclusiveMinimum": 0},
        "pids_limit": {"type": ["integer", "null"], "exclusiveMinimum": 0},
        "network_enabled": {"type": ["boolean", "null"]},
    },
}


def upgrade() -> None:
    """Add a ``runner`` block to ``testing.temporal``'s ``schema``.

    The existing schema only validates the ``language`` discriminator.
    We merge the new runner block in via ``jsonb_set`` so we don't
    clobber whatever else may have been added since the original seed.
    """
    runner_json = json.dumps(_RUNNER_SCHEMA).replace("'", "''")
    op.execute(
        f"""
        UPDATE service_type
           SET schema = jsonb_set(
                 COALESCE(schema, '{{"type":"object","properties":{{}}}}'::jsonb),
                 '{{properties,runner}}',
                 '{runner_json}'::jsonb,
                 true
               )
         WHERE path = 'testing.temporal';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE service_type
           SET schema = schema #- '{properties,runner}'
         WHERE path = 'testing.temporal';
        """
    )
