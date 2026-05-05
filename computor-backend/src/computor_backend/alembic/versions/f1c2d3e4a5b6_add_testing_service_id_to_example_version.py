"""add testing_service_id to example_version

Revision ID: f1c2d3e4a5b6
Revises: e0f1a2b3c4d5
Create Date: 2026-05-05 12:00:00.000000

Move the canonical "which service runs tests for this example" link from a
runtime YAML lookup at assignment time onto a real foreign-key column on
``example_version``. Resolving the slug→service mapping happens once, at
upload, and is then stable for every assignment that follows.

Pre-existing rows are backfilled in Python (we need yaml parsing). Rows
whose meta.yaml lacks ``properties.executionBackend.slug`` or whose slug
no longer resolves to an enabled, non-archived ``service`` are left with
``testing_service_id = NULL`` — the application will surface those when
someone tries to assign them.

After ``example_version.testing_service_id`` is populated, the migration
also backfills ``course_content.testing_service_id`` for any submittable
content that already has a deployment but never got the previous
best-effort auto-link to fire (rows assigned before commit e1712c9).
"""
from typing import Sequence, Union

import yaml
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f1c2d3e4a5b6'
down_revision: Union[str, None] = 'e0f1a2b3c4d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _extract_execution_backend_slug(meta_yaml: str) -> str | None:
    """Mirror of ExampleVersion.get_execution_backend_slug — kept inline
    so this migration is self-contained and survives future refactors of
    the model.
    """
    if not meta_yaml:
        return None
    try:
        data = yaml.safe_load(meta_yaml)
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    properties = data.get('properties')
    if not isinstance(properties, dict):
        return None
    execution_backend = properties.get('executionBackend')
    if not isinstance(execution_backend, dict):
        return None
    return execution_backend.get('slug')


def upgrade() -> None:
    # 1. Add nullable column + supporting index. Stays nullable: pre-
    #    existing rows whose slug we can't resolve must be allowed to
    #    persist; we don't want the migration to wedge on legacy bad data.
    op.add_column(
        'example_version',
        sa.Column('testing_service_id', postgresql.UUID(), nullable=True),
    )
    op.create_index(
        'ix_example_version_testing_service_id',
        'example_version',
        ['testing_service_id'],
    )
    op.create_foreign_key(
        'example_version_testing_service_id_fkey',
        'example_version', 'service',
        ['testing_service_id'], ['id'],
        ondelete='RESTRICT',
    )

    # 2. Backfill example_version.testing_service_id by parsing meta.yaml
    #    and resolving the slug against the service table. Iterate in
    #    Python since Postgres doesn't speak YAML.
    bind = op.get_bind()

    rows = bind.execute(
        sa.text(
            "SELECT id, meta_yaml FROM example_version "
            "WHERE meta_yaml IS NOT NULL AND testing_service_id IS NULL"
        )
    ).fetchall()

    # Build slug → service.id once. Only enabled, non-archived services
    # qualify — same predicate used by the runtime resolver, so the
    # migration matches the application's view of "live" services.
    service_rows = bind.execute(
        sa.text(
            "SELECT id, slug FROM service "
            "WHERE enabled = TRUE AND archived_at IS NULL"
        )
    ).fetchall()
    slug_to_service_id = {r.slug: r.id for r in service_rows}

    update_stmt = sa.text(
        "UPDATE example_version SET testing_service_id = :sid WHERE id = :vid"
    )

    matched = 0
    no_slug = 0
    no_service = 0
    for row in rows:
        slug = _extract_execution_backend_slug(row.meta_yaml)
        if not slug:
            no_slug += 1
            continue
        service_id = slug_to_service_id.get(slug)
        if not service_id:
            no_service += 1
            continue
        bind.execute(update_stmt, {"sid": service_id, "vid": row.id})
        matched += 1

    # Surface the backfill outcome in the migration log so an operator
    # running ``alembic upgrade`` can immediately see how many legacy
    # versions are still orphaned and need follow-up.
    op.execute(
        sa.text(
            "DO $$ BEGIN "
            "RAISE NOTICE 'example_version.testing_service_id backfill: "
            f"matched={matched}, no_executionBackend_slug={no_slug}, "
            f"unresolved_slug={no_service}'; "
            "END $$;"
        )
    )

    # 3. Backfill course_content.testing_service_id from the now-populated
    #    example_version FK, but only for content that currently has a
    #    live deployment and no testing service yet. This covers content
    #    assigned before the runtime auto-link existed (commit e1712c9,
    #    2026-03-16) as well as anything where the auto-link silently
    #    no-op'd.
    op.execute(
        """
        UPDATE course_content cc
           SET testing_service_id = ev.testing_service_id
          FROM course_content_deployment d
          JOIN example_version ev ON ev.id = d.example_version_id
         WHERE d.course_content_id = cc.id
           AND d.deployment_status <> 'unassigned'
           AND ev.testing_service_id IS NOT NULL
           AND cc.testing_service_id IS NULL;
        """
    )


def downgrade() -> None:
    op.drop_constraint(
        'example_version_testing_service_id_fkey',
        'example_version',
        type_='foreignkey',
    )
    op.drop_index(
        'ix_example_version_testing_service_id',
        table_name='example_version',
    )
    op.drop_column('example_version', 'testing_service_id')
