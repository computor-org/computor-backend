---
name: computor-backend-data
description: Computor backend persistence — SQLAlchemy models, Alembic migrations, repositories and query construction. Use when adding or altering a table, writing a migration, changing a relationship or cascade, or optimizing a query in computor-fullstack/computor-backend.
---

# Computor backend — data layer

You own `computor_backend/model/` (SQLAlchemy), `alembic/versions/` (74 revisions
and counting) and `repositories/`.

## Migrations

- Find the current head with **`alembic heads`** — never by grepping revision
  files; several branches carry their own and grep picks the wrong one.
- psql access in dev: container `docker-postgres-1`, port **5437**, database
  `computor`. Port **5439** is the *Coder* postgres — never point a Computor
  migration or wipe at it.
- Every migration needs a working `downgrade()`. If a downgrade genuinely cannot
  restore the data, say so in the docstring rather than leaving a silent `pass`.
- Data migrations run against production rows: batch them, and never assume a
  column you just added is populated.

## Cascades are the dangerous part

Deletes in this schema fan out further than they look — a cascade misconfigured
on `Result` once wiped `CourseContent` rows (issue #289). Before adding or
changing `ondelete=` / `cascade=`, trace the full path both in the ORM
relationship **and** in the DB-level FK, because they can disagree: SQLAlchemy's
`cascade="all, delete-orphan"` and Postgres `ON DELETE CASCADE` are separate
mechanisms and only the second applies to raw SQL and to rows the session never
loaded. `business_logic/cascade_deletion.py` is the deliberate, explicit deletion
path — prefer extending it over adding another automatic cascade.

Hierarchy deletes are bottom-up by design: organization and course-family deletes
409 while children exist. That is intended, not a bug to "fix".

## Models and repositories

- Models in `model/`, one module per aggregate (`course.py`, `example.py`,
  `result.py`, …). Naming and mixins follow `model/base.py`.
- Query logic belongs in `repositories/`, not in `business_logic/` and never in
  `api/`. Complex reads already have homes — `course_content_queries.py`,
  `course_content_subqueries.py`, `grading_read.py`.
- Watch for cartesian joins when a query touches course contents plus two
  collections; this has bitten before (`fix/2026.10-course-contents-cartesian-join`).
  Use subqueries or `selectinload`, and check the row count, not just the shape.
- **UUID columns want strings in filters.** A `uuid.UUID` object in a filter
  raises `StatementError` → 500. Convert at the boundary.

## Boundaries

SQLAlchemy models are **not** DTOs and must never leak past `business_logic/`.
API-facing pydantic models live in `computor-types`, which is forbidden from
importing `sqlalchemy` at all (enforced by
`scripts/check_forbidden_imports.py` in the pre-commit hook). Converting a model
to a DTO is `SomeGet.model_validate(row)` at the business-logic edge.

For endpoint shape and DTO families, hand off to `computor-backend-api`.
