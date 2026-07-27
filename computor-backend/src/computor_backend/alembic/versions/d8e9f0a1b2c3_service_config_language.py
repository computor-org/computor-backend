"""backfill service.config.language and widen the testing.temporal enum

The test runner is now selected by ``Service.config.language``
(``TestingBackendFactory``), replacing a hardcoded slug→backend table that
only recognised the eight ``itpcp.exec.*`` names. Services created before
this have no ``config.language`` — the deployment YAML carried ``language:``
as a sibling of ``config:`` and the bootstrap seeder dropped it — so they
must be backfilled or they stop dispatching.

The slug→language mapping lives here, in a one-shot data migration, rather
than in the code: it is exactly the coupling being removed, and it should
not survive this migration.

Also widens the ``testing.temporal`` ServiceType schema enum, which listed
only python/matlab/java/cpp even though the computor-test CLI has always
supported octave, r, julia, c, fortran and document.

Revision ID: d8e9f0a1b2c3
Revises: c7d8e9f0a1b2
Create Date: 2026-07-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd8e9f0a1b2c3'
down_revision: Union[str, None] = 'c7d8e9f0a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_LANGUAGES = '["python","octave","r","julia","c","cpp","fortran","document","matlab"]'


def upgrade() -> None:
    # 1. Widen the declared language enum for the seeded testing type.
    op.execute(f"""
        UPDATE service_type
           SET schema = jsonb_set(
                   COALESCE(schema, '{{}}'::jsonb),
                   '{{properties,language,enum}}',
                   '{_LANGUAGES}'::jsonb,
                   true
               )
         WHERE path::text = 'testing.temporal'
           AND schema IS NOT NULL;
    """)

    # 2. Backfill config.language from the legacy slug suffix, once.
    op.execute("""
        UPDATE service s
           SET config = COALESCE(s.config, '{}'::jsonb)
                        || jsonb_build_object('language',
               CASE
                   WHEN s.slug LIKE '%%.py'      OR s.slug = 'temporal:python' THEN 'python'
                   WHEN s.slug LIKE '%%.oct'                                   THEN 'octave'
                   WHEN s.slug LIKE '%%.r'                                     THEN 'r'
                   WHEN s.slug LIKE '%%.julia'                                 THEN 'julia'
                   WHEN s.slug LIKE '%%.fortran'                               THEN 'fortran'
                   WHEN s.slug LIKE '%%.doc'                                   THEN 'document'
                   WHEN s.slug LIKE '%%.mat'     OR s.slug = 'temporal:matlab' THEN 'matlab'
                   WHEN s.slug LIKE '%%.c'                                     THEN 'c'
               END)
          FROM service_type st
         WHERE st.id = s.service_type_id
           AND st.category = 'testing'
           AND NOT (COALESCE(s.config, '{}'::jsonb) ? 'language')
           AND s.slug ~ '\\.(py|oct|r|julia|c|fortran|doc|mat)$';
    """)

    # 3. Refuse to complete silently if anything was missed. A testing service
    #    with no language raises at dispatch, and finding that out on a
    #    student's submission is far worse than finding it out here.
    conn = op.get_bind()
    orphans = conn.execute(sa.text("""
        SELECT s.slug
          FROM service s
          JOIN service_type st ON st.id = s.service_type_id
         WHERE st.category = 'testing'
           AND s.archived_at IS NULL
           AND COALESCE(s.config, '{}'::jsonb)->>'language' IS NULL
    """)).fetchall()
    if orphans:
        slugs = ", ".join(row[0] for row in orphans)
        raise RuntimeError(
            "Cannot complete migration: these testing services have no "
            f"config.language and would stop running tests: {slugs}. "
            "Set config.language on each (one of python, octave, r, julia, c, "
            "cpp, fortran, document, matlab) and re-run."
        )


def downgrade() -> None:
    op.execute("""
        UPDATE service s
           SET config = s.config - 'language'
          FROM service_type st
         WHERE st.id = s.service_type_id
           AND st.category = 'testing';
    """)
    op.execute("""
        UPDATE service_type
           SET schema = jsonb_set(
                   schema,
                   '{properties,language,enum}',
                   '["python","matlab","java","cpp"]'::jsonb,
                   true
               )
         WHERE path::text = 'testing.temporal'
           AND schema IS NOT NULL;
    """)
