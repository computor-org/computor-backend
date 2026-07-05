"""add example_manager role

Introduces the ``_example_manager`` global role, which owns the example
library: uploading examples and versions, editing dependencies, and deleting
examples / versions / repositories. Reading examples and assigning them to
courses is unchanged — a per-course ``_lecturer`` and ``_organization_manager``
keep read access, and assignment stays gated on course membership.

The organization manager previously held the example *authoring* claims
(``example:create/update/upload`` and ``example_repository:create/update``).
Those move to ``_example_manager`` here. Because ``db_apply_roles`` at startup
is insert-only (``ON CONFLICT DO NOTHING``), it cannot retract them — this
migration deletes them explicitly so the restriction takes effect on existing
databases. The manager keeps ``example``/``example_repository`` read claims.

Revision ID: e1f2a3b4c5d6
Revises: dd2e3f4a5b6c
Create Date: 2026-07-05

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, None] = 'dd2e3f4a5b6c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Claims that define what _example_manager may do. Kept in sync with
# computor_backend.permissions.role_setup.claims_example_manager (that function
# re-applies them at startup; both are insert-only / idempotent).
_EXAMPLE_MANAGER_CLAIMS = [
    "example:get",
    "example:list",
    "example:download",
    "example:create",
    "example:update",
    "example:upload",
    "example:delete",
    "example_repository:get",
    "example_repository:list",
    "example_repository:create",
    "example_repository:update",
    "example_repository:delete",
]

# Authoring claims to strip from _organization_manager (read claims stay).
_ORG_MANAGER_REVOKED_CLAIMS = [
    "example:create",
    "example:update",
    "example:upload",
    "example_repository:create",
    "example_repository:update",
]


def _values_sql(role_id: str, claims: list[str]) -> str:
    return ",\n          ".join(
        f"('{role_id}', 'permissions', '{c}')" for c in claims
    )


def upgrade() -> None:
    # 1. Create the global role.
    op.execute(
        """
        INSERT INTO role (id, title, description, builtin)
        VALUES (
            '_example_manager',
            'Example Manager',
            'Owns the example library: upload/create/delete examples, versions, and repositories. Reading and assigning examples to courses remains with lecturers and organization managers.',
            true
        )
        ON CONFLICT (id) DO NOTHING;
        """
    )

    # 2. Seed its claims (startup re-applies these idempotently; seeding here
    #    keeps the role functional straight after ``alembic upgrade``).
    op.execute(
        f"""
        INSERT INTO role_claim (role_id, claim_type, claim_value)
        VALUES
          {_values_sql('_example_manager', _EXAMPLE_MANAGER_CLAIMS)}
        ON CONFLICT (role_id, claim_type, claim_value) DO NOTHING;
        """
    )

    # 3. Revoke example authoring claims from _organization_manager (reads stay).
    revoked = ", ".join(f"'{c}'" for c in _ORG_MANAGER_REVOKED_CLAIMS)
    op.execute(
        f"""
        DELETE FROM role_claim
        WHERE role_id = '_organization_manager'
          AND claim_type = 'permissions'
          AND claim_value IN ({revoked});
        """
    )


def downgrade() -> None:
    # Restore the authoring claims on _organization_manager.
    op.execute(
        f"""
        INSERT INTO role_claim (role_id, claim_type, claim_value)
        VALUES
          {_values_sql('_organization_manager', _ORG_MANAGER_REVOKED_CLAIMS)}
        ON CONFLICT (role_id, claim_type, claim_value) DO NOTHING;
        """
    )

    # Remove the _example_manager role and everything referencing it.
    op.execute(
        """
        DELETE FROM role_claim WHERE role_id = '_example_manager';
        DELETE FROM user_role  WHERE role_id = '_example_manager';
        DELETE FROM role        WHERE id = '_example_manager';
        """
    )
