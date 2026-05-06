"""add typed meta columns to example_version, drop meta_yaml

Revision ID: c4d5e6f7a8b9
Revises: f1c2d3e4a5b6
Create Date: 2026-05-05 13:00:00.000000

Replace the single ``meta_yaml TEXT`` blob on ``example_version`` with a
typed schema:

- ``meta`` (JSONB)            — full parsed meta.yaml (round-trip storage)
- ``title``, ``description``, ``language``, ``license`` — promoted scalars
- ``execution_backend`` (JSONB) — full ``properties.executionBackend`` dict
                                  (slug + version + settings)
- ``student_submission_files``, ``additional_files``, ``student_templates``,
  ``test_files`` (TEXT[])    — promoted file lists used by the student-
                                template / tutor flows

The ``testing_service_id`` FK added in the previous migration stays put;
it remains the resolved Service.id derived from
``properties.executionBackend.slug``. The new ``execution_backend`` JSONB
preserves the original meta.yaml block verbatim (slug + version +
settings), so a future Service rename doesn't lose the historical
declaration.

Strategy:
  1. Add new columns (nullable).
  2. Backfill in Python: parse each row's ``meta_yaml``, populate.
  3. ``meta`` becomes NOT NULL — unparseable rows store a structured
     fallback so the constraint holds and the bad input is recoverable.
  4. Drop ``meta_yaml``.
"""
from typing import Sequence, Union

import yaml
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c4d5e6f7a8b9'
down_revision: Union[str, None] = 'f1c2d3e4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _split_promoted(parsed: dict | None, raw_yaml: str | None) -> dict:
    """Pull promoted fields out of a parsed meta.yaml dict.

    Returns a flat dict ready to feed UPDATE bind parameters. If the
    YAML couldn't be parsed (or wasn't a dict), we still produce a row:
    ``meta`` gets a structured fallback containing the parse error and
    a truncated raw payload so an admin can fix the source later.
    """
    if not isinstance(parsed, dict):
        return {
            "meta": {
                "_parse_error": "meta.yaml did not parse to a dict",
                "_raw": (raw_yaml or "")[:2000],
            },
            "title": None,
            "description": None,
            "language": None,
            "license": None,
            "execution_backend": None,
            "student_submission_files": [],
            "additional_files": [],
            "student_templates": [],
            "test_files": [],
        }

    properties = parsed.get("properties")
    if not isinstance(properties, dict):
        properties = {}

    def _str_list(value) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if item is not None]

    return {
        "meta": parsed,
        "title": parsed.get("title"),
        "description": parsed.get("description"),
        "language": parsed.get("language"),
        "license": parsed.get("license"),
        "execution_backend": (
            properties.get("executionBackend")
            if isinstance(properties.get("executionBackend"), dict)
            else None
        ),
        "student_submission_files": _str_list(properties.get("studentSubmissionFiles")),
        "additional_files": _str_list(properties.get("additionalFiles")),
        "student_templates": _str_list(properties.get("studentTemplates")),
        "test_files": _str_list(properties.get("testFiles")),
    }


def upgrade() -> None:
    # 1. Add columns nullable.
    op.add_column('example_version', sa.Column('meta', postgresql.JSONB(), nullable=True))
    op.add_column('example_version', sa.Column('title', sa.String(length=255), nullable=True))
    op.add_column('example_version', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('example_version', sa.Column('language', sa.String(length=16), nullable=True))
    op.add_column('example_version', sa.Column('license', sa.String(length=255), nullable=True))
    op.add_column(
        'example_version',
        sa.Column('execution_backend', postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        'example_version',
        sa.Column(
            'student_submission_files',
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
    )
    op.add_column(
        'example_version',
        sa.Column(
            'additional_files',
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
    )
    op.add_column(
        'example_version',
        sa.Column(
            'student_templates',
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
    )
    op.add_column(
        'example_version',
        sa.Column(
            'test_files',
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
    )

    # 2. Backfill from existing meta_yaml.
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, meta_yaml FROM example_version")
    ).fetchall()

    update_stmt = sa.text(
        """
        UPDATE example_version
           SET meta = CAST(:meta AS JSONB),
               title = :title,
               description = :description,
               language = :language,
               license = :license,
               execution_backend = CAST(:execution_backend AS JSONB),
               student_submission_files = :student_submission_files,
               additional_files = :additional_files,
               student_templates = :student_templates,
               test_files = :test_files
         WHERE id = :id
        """
    )

    import json as _json

    parsed_ok = 0
    parse_errors = 0
    for row in rows:
        raw = row.meta_yaml
        try:
            parsed = yaml.safe_load(raw) if raw else None
        except yaml.YAMLError:
            parsed = None
            parse_errors += 1

        promoted = _split_promoted(parsed, raw)

        bind.execute(
            update_stmt,
            {
                "id": row.id,
                "meta": _json.dumps(promoted["meta"]),
                "title": promoted["title"],
                "description": promoted["description"],
                "language": promoted["language"],
                "license": promoted["license"],
                "execution_backend": (
                    _json.dumps(promoted["execution_backend"])
                    if promoted["execution_backend"] is not None
                    else None
                ),
                "student_submission_files": promoted["student_submission_files"],
                "additional_files": promoted["additional_files"],
                "student_templates": promoted["student_templates"],
                "test_files": promoted["test_files"],
            },
        )

        if isinstance(parsed, dict):
            parsed_ok += 1

    op.execute(
        sa.text(
            "DO $$ BEGIN "
            f"RAISE NOTICE 'example_version meta backfill: parsed_ok={parsed_ok}, "
            f"yaml_errors={parse_errors}, total={len(rows)}'; "
            "END $$;"
        )
    )

    # 3. Tighten ``meta`` — backfill guarantees every row has a value.
    op.alter_column(
        'example_version',
        'meta',
        existing_type=postgresql.JSONB(),
        nullable=False,
    )

    # Server defaults on the array columns served the migration; drop
    # them so the application is the only writer going forward and we
    # don't accumulate empty arrays on rows that genuinely didn't
    # declare files.
    op.alter_column('example_version', 'student_submission_files', server_default=None)
    op.alter_column('example_version', 'additional_files', server_default=None)
    op.alter_column('example_version', 'student_templates', server_default=None)
    op.alter_column('example_version', 'test_files', server_default=None)

    # 4. Drop the old text blob.
    op.drop_column('example_version', 'meta_yaml')


def downgrade() -> None:
    """Re-create ``meta_yaml`` and rehydrate it from JSONB.

    The downgrade path is best-effort — it dumps the JSONB back to
    YAML so the column has a usable value, but exact whitespace /
    comments from the original meta.yaml file are lost (that
    information was already lost on the upgrade backfill).
    """
    op.add_column(
        'example_version',
        sa.Column('meta_yaml', sa.Text(), nullable=True),
    )

    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, meta FROM example_version WHERE meta IS NOT NULL")
    ).fetchall()

    for row in rows:
        try:
            rendered = yaml.safe_dump(row.meta, default_flow_style=False, sort_keys=False)
        except Exception:
            rendered = ""
        bind.execute(
            sa.text("UPDATE example_version SET meta_yaml = :y WHERE id = :id"),
            {"y": rendered, "id": row.id},
        )

    op.alter_column('example_version', 'meta_yaml', nullable=False)

    op.drop_column('example_version', 'test_files')
    op.drop_column('example_version', 'student_templates')
    op.drop_column('example_version', 'additional_files')
    op.drop_column('example_version', 'student_submission_files')
    op.drop_column('example_version', 'execution_backend')
    op.drop_column('example_version', 'license')
    op.drop_column('example_version', 'language')
    op.drop_column('example_version', 'description')
    op.drop_column('example_version', 'title')
    op.drop_column('example_version', 'meta')
