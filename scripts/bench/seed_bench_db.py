#!/usr/bin/env python3
"""Build a throwaway ``computor_bench`` database with a synthetic course world.

Why a separate database: the dev ``computor`` database holds real work and is
far too small to measure anything (a few hundred submission groups). Query
plans only diverge once the tables are big enough for Postgres to stop
choosing a sequential scan for everything, so timings taken against the dev
data would be noise. This script therefore never writes to ``computor`` — it
drops and rebuilds its own database next to it in the same server.

The schema comes from ``alembic upgrade head`` rather than a dump of the dev
database, so the benchmark reflects the migrations as committed (and the
initial migration already seeds ``course_content_kind`` / ``course_role``).

Rows are generated with ``INSERT … SELECT FROM generate_series`` and
deterministic ``md5(...)::uuid`` primary keys, so a table can reference
another without reading ids back, and two runs at the same scale produce
byte-identical data — a benchmark that reseeds mid-comparison stays fair.

Usage::

    python scripts/bench/seed_bench_db.py                # default scale
    python scripts/bench/seed_bench_db.py --scale 2      # twice the rows
    python scripts/bench/seed_bench_db.py --keep-schema  # reseed data only
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import psycopg2
from psycopg2 import sql

REPO_ROOT = Path(__file__).resolve().parents[2]
BENCH_DB = os.environ.get("BENCH_DB", "computor_bench")


def _conn_params(dbname: str) -> dict:
    return {
        "host": os.environ.get("POSTGRES_HOST", "localhost"),
        "port": os.environ.get("POSTGRES_PORT", "5432"),
        "user": os.environ["POSTGRES_USER"],
        "password": os.environ["POSTGRES_PASSWORD"],
        "dbname": dbname,
    }


def recreate_database() -> None:
    """Drop and recreate ``BENCH_DB``. Refuses to touch anything else."""
    if BENCH_DB in ("computor", "postgres", "coder"):
        raise SystemExit(f"refusing to drop {BENCH_DB!r} — that is not a bench database")

    conn = psycopg2.connect(**_conn_params("postgres"))
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
            (BENCH_DB,),
        )
        cur.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(BENCH_DB)))
        cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(BENCH_DB)))
    conn.close()
    print(f"  recreated database {BENCH_DB}")


def run_migrations() -> None:
    """``alembic upgrade head`` against the bench database."""
    env = dict(os.environ, POSTGRES_DB=BENCH_DB)
    src = REPO_ROOT / "computor-backend" / "src"
    env["PYTHONPATH"] = f"{src}:{env.get('PYTHONPATH', '')}"
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=src / "computor_backend",
        env=env,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    print("  schema migrated to head")


# ---------------------------------------------------------------------------
# Synthetic world
#
# Shape, at scale 1: one organization -> one course family -> COURSES courses.
# Each course gets UNITS unit-kind contents and ASSIGNMENTS assignment-kind
# contents hanging off them, STUDENTS students spread over GROUPS course
# groups, TUTORS tutors and the one lecturer shared by every course.
#
# Student 0 is enrolled in *every* course on purpose: the student dashboard
# query runs without a course filter, so the interesting case is the one that
# spans courses rather than the single-course one.
# ---------------------------------------------------------------------------

COURSES = 3
UNITS = 10
GROUPS = 4
TUTORS = 5

# Results carry a distinct ``created_at`` per row. Ties there make the
# dashboard's latest-result join match several rows at once — the row blow-up
# ``course_content_queries`` documents — which would measure a pathology
# instead of the query.
DDL_STEPS: list[tuple[str, str]] = []


def build_steps(students: int, assignments: int) -> list[tuple[str, str]]:
    """(label, SQL) pairs, in dependency order.

    ``students`` and ``assignments`` are ints this script computes, never user
    text, so interpolating them into the SQL is safe.
    """
    per_course_users = students + TUTORS
    lecturer_ix = COURSES * per_course_users  # the one user after every course's block

    return [
        ("organization", """
            INSERT INTO organization (id, path, organization_type, title)
            VALUES (md5('bench:org')::uuid, 'bench', 'organization', 'Bench Organization');
        """),
        ("course_family", """
            INSERT INTO course_family (id, path, organization_id, title)
            VALUES (md5('bench:family')::uuid, 'bench', md5('bench:org')::uuid, 'Bench Family');
        """),
        ("course", f"""
            INSERT INTO course (id, path, course_family_id, organization_id, title)
            SELECT md5('bench:course:' || c)::uuid,
                   ('bench' || c)::ltree,
                   md5('bench:family')::uuid,
                   md5('bench:org')::uuid,
                   'Bench Course ' || c
            FROM generate_series(0, {COURSES - 1}) c;
        """),
        ("course_group", f"""
            INSERT INTO course_group (id, course_id, title)
            SELECT md5('bench:cg:' || c || ':' || g)::uuid,
                   md5('bench:course:' || c)::uuid,
                   'Group ' || g
            FROM generate_series(0, {COURSES - 1}) c,
                 generate_series(0, {GROUPS - 1}) g;
        """),
        ("course_content_type", f"""
            INSERT INTO course_content_type (id, slug, title, course_content_kind_id, course_id)
            SELECT md5('bench:cct:unit:' || c)::uuid, 'bench-unit', 'Unit',
                   'unit', md5('bench:course:' || c)::uuid
            FROM generate_series(0, {COURSES - 1}) c
            UNION ALL
            SELECT md5('bench:cct:asg:' || c)::uuid, 'bench-assignment', 'Assignment',
                   'assignment', md5('bench:course:' || c)::uuid
            FROM generate_series(0, {COURSES - 1}) c;
        """),
        ("user", f"""
            INSERT INTO "user" (id, given_name, family_name, email)
            SELECT md5('bench:user:' || u)::uuid,
                   'Bench', 'User' || u,
                   'bench.user' || u || '@bench.local'
            FROM generate_series(0, {lecturer_ix}) u;
        """),
        # Students first (they need a course group), then tutors, then the
        # shared lecturer. Student 0 additionally joins every other course.
        ("course_member (students)", f"""
            INSERT INTO course_member (id, user_id, course_id, course_role_id, course_group_id)
            SELECT md5('bench:cm:' || c || ':' || (c * {per_course_users} + s))::uuid,
                   md5('bench:user:' || (c * {per_course_users} + s))::uuid,
                   md5('bench:course:' || c)::uuid,
                   '_student',
                   md5('bench:cg:' || c || ':' || (s % {GROUPS}))::uuid
            FROM generate_series(0, {COURSES - 1}) c,
                 generate_series(0, {students - 1}) s;
        """),
        ("course_member (student 0 everywhere)", f"""
            INSERT INTO course_member (id, user_id, course_id, course_role_id, course_group_id)
            SELECT md5('bench:cm:' || c || ':0')::uuid,
                   md5('bench:user:0')::uuid,
                   md5('bench:course:' || c)::uuid,
                   '_student',
                   md5('bench:cg:' || c || ':0')::uuid
            FROM generate_series(1, {COURSES - 1}) c;
        """),
        ("course_member (tutors)", f"""
            INSERT INTO course_member (id, user_id, course_id, course_role_id)
            SELECT md5('bench:cm:' || c || ':' || (c * {per_course_users} + {students} + t))::uuid,
                   md5('bench:user:' || (c * {per_course_users} + {students} + t))::uuid,
                   md5('bench:course:' || c)::uuid,
                   '_tutor'
            FROM generate_series(0, {COURSES - 1}) c,
                 generate_series(0, {TUTORS - 1}) t;
        """),
        ("course_member (lecturer)", f"""
            INSERT INTO course_member (id, user_id, course_id, course_role_id)
            SELECT md5('bench:cm:lecturer:' || c)::uuid,
                   md5('bench:user:' || {lecturer_ix})::uuid,
                   md5('bench:course:' || c)::uuid,
                   '_lecturer'
            FROM generate_series(0, {COURSES - 1}) c;
        """),
        ("student_profile", f"""
            INSERT INTO student_profile (id, user_id, organization_id, student_id)
            SELECT md5('bench:sp:' || u)::uuid,
                   md5('bench:user:' || u)::uuid,
                   md5('bench:org')::uuid,
                   'S' || lpad(u::text, 8, '0')
            FROM generate_series(0, {lecturer_ix}) u;
        """),
        # Units before assignments: trg_validate_course_content_hierarchy
        # resolves each assignment's parent by path at insert time.
        ("course_content (units)", f"""
            INSERT INTO course_content (id, path, course_id, course_content_type_id,
                                        position, course_content_kind_id, is_submittable, title)
            SELECT md5('bench:unit:' || c || ':' || k)::uuid,
                   ('u' || lpad(k::text, 3, '0'))::ltree,
                   md5('bench:course:' || c)::uuid,
                   md5('bench:cct:unit:' || c)::uuid,
                   k, 'unit', false, 'Unit ' || k
            FROM generate_series(0, {COURSES - 1}) c,
                 generate_series(0, {UNITS - 1}) k;
        """),
        ("course_content (assignments)", f"""
            INSERT INTO course_content (id, path, course_id, course_content_type_id,
                                        position, course_content_kind_id, is_submittable, title)
            SELECT md5('bench:asg:' || c || ':' || a)::uuid,
                   ('u' || lpad((a % {UNITS})::text, 3, '0') || '.a' || lpad(a::text, 3, '0'))::ltree,
                   md5('bench:course:' || c)::uuid,
                   md5('bench:cct:asg:' || c)::uuid,
                   a, 'assignment', true, 'Assignment ' || a
            FROM generate_series(0, {COURSES - 1}) c,
                 generate_series(0, {assignments - 1}) a;
        """),
        ("submission_group", f"""
            INSERT INTO submission_group (id, course_id, course_content_id, max_group_size)
            SELECT md5('bench:sg:' || c || ':' || a || ':' || s)::uuid,
                   md5('bench:course:' || c)::uuid,
                   md5('bench:asg:' || c || ':' || a)::uuid,
                   1
            FROM generate_series(0, {COURSES - 1}) c,
                 generate_series(0, {assignments - 1}) a,
                 generate_series(0, {students - 1}) s;
        """),
        ("submission_group_member", f"""
            INSERT INTO submission_group_member (id, course_id, submission_group_id, course_member_id)
            SELECT md5('bench:sgm:' || c || ':' || a || ':' || s)::uuid,
                   md5('bench:course:' || c)::uuid,
                   md5('bench:sg:' || c || ':' || a || ':' || s)::uuid,
                   md5('bench:cm:' || c || ':' || (c * {per_course_users} + s))::uuid
            FROM generate_series(0, {COURSES - 1}) c,
                 generate_series(0, {assignments - 1}) a,
                 generate_series(0, {students - 1}) s
            WHERE s > 0;
        """),
        # Student 0's memberships point at its own per-course member row.
        ("submission_group_member (student 0)", f"""
            INSERT INTO submission_group_member (id, course_id, submission_group_id, course_member_id)
            SELECT md5('bench:sgm:' || c || ':' || a || ':0')::uuid,
                   md5('bench:course:' || c)::uuid,
                   md5('bench:sg:' || c || ':' || a || ':0')::uuid,
                   md5('bench:cm:' || c || ':0')::uuid
            FROM generate_series(0, {COURSES - 1}) c,
                 generate_series(0, {assignments - 1}) a;
        """),
        # Two artifacts for every second student: n=0 is a practice run,
        # n=1 the official submission the grading path keys off.
        ("submission_artifact", f"""
            INSERT INTO submission_artifact (id, submission_group_id, uploaded_by_course_member_id,
                                             file_size, bucket_name, object_key, submit,
                                             version_identifier, created_at, uploaded_at)
            SELECT md5('bench:sa:' || c || ':' || a || ':' || s || ':' || n)::uuid,
                   md5('bench:sg:' || c || ':' || a || ':' || s)::uuid,
                   CASE WHEN s = 0 THEN md5('bench:cm:' || c || ':0')::uuid
                        ELSE md5('bench:cm:' || c || ':' || (c * {per_course_users} + s))::uuid END,
                   4096, 'submissions',
                   'bench/' || c || '/' || a || '/' || s || '/' || n,
                   n = 1,
                   substr(md5('bench:ver:' || c || ':' || a || ':' || s || ':' || n), 1, 40),
                   timestamptz '2026-01-01 00:00:00+00'
                     + ((((c * {assignments} + a) * {students} + s) * 2 + n) * interval '1 second'),
                   timestamptz '2026-01-01 00:00:00+00'
                     + ((((c * {assignments} + a) * {students} + s) * 2 + n) * interval '1 second')
            FROM generate_series(0, {COURSES - 1}) c,
                 generate_series(0, {assignments - 1}) a,
                 generate_series(0, {students - 1}) s,
                 generate_series(0, 1) n
            WHERE s % 2 = 0;
        """),
        # Half the submitted artifacts carry a grade, cycling through the four
        # GradingStatus values so the status filter has something to select.
        ("submission_grade", f"""
            INSERT INTO submission_grade (id, artifact_id, graded_by_course_member_id,
                                          grade, status, graded_at)
            SELECT md5('bench:grd:' || c || ':' || a || ':' || s)::uuid,
                   md5('bench:sa:' || c || ':' || a || ':' || s || ':1')::uuid,
                   md5('bench:cm:' || c || ':' || (c * {per_course_users} + {students} + (s % {TUTORS})))::uuid,
                   (s % 10) / 10.0,
                   (a + s) % 4,
                   timestamptz '2026-02-01 00:00:00+00'
                     + (((c * {assignments} + a) * {students} + s) * interval '1 second')
            FROM generate_series(0, {COURSES - 1}) c,
                 generate_series(0, {assignments - 1}) a,
                 generate_series(0, {students - 1}) s
            WHERE s % 4 = 0;
        """),
        # One FINISHED result per artifact plus one FAILED retry. Only FAILED
        # (a retryable status) may repeat per artifact — the partial unique
        # index on ``result`` allows exactly one non-retryable row there.
        ("result", f"""
            INSERT INTO result (id, course_member_id, submission_artifact_id, submission_group_id,
                                course_content_id, course_content_type_id, version_identifier,
                                status, test_system_id, grade, created_at)
            SELECT md5('bench:res:' || c || ':' || a || ':' || s || ':' || n || ':' || r)::uuid,
                   CASE WHEN s = 0 THEN md5('bench:cm:' || c || ':0')::uuid
                        ELSE md5('bench:cm:' || c || ':' || (c * {per_course_users} + s))::uuid END,
                   md5('bench:sa:' || c || ':' || a || ':' || s || ':' || n)::uuid,
                   md5('bench:sg:' || c || ':' || a || ':' || s)::uuid,
                   md5('bench:asg:' || c || ':' || a)::uuid,
                   md5('bench:cct:asg:' || c)::uuid,
                   substr(md5('bench:rver:' || c || ':' || a || ':' || s || ':' || n || ':' || r), 1, 40),
                   CASE WHEN r = 0 THEN 1 ELSE 0 END,
                   'bench-test-system',
                   (s % 10) / 10.0,
                   timestamptz '2026-01-01 12:00:00+00'
                     + (((((c * {assignments} + a) * {students} + s) * 2 + n) * 2 + r) * interval '1 second')
            FROM generate_series(0, {COURSES - 1}) c,
                 generate_series(0, {assignments - 1}) a,
                 generate_series(0, {students - 1}) s,
                 generate_series(0, 1) n,
                 generate_series(0, 1) r
            WHERE s % 2 = 0;
        """),
        # Messages hang off contents and submission groups so the unread
        # counters in the dashboard query have rows to aggregate.
        ("message", f"""
            INSERT INTO message (id, author_id, level, content, course_id, course_content_id,
                                 submission_group_id, created_at)
            SELECT md5('bench:msg:' || c || ':' || a || ':' || s)::uuid,
                   CASE WHEN s = 0 THEN md5('bench:user:' || {lecturer_ix})::uuid
                        ELSE md5('bench:user:' || (c * {per_course_users} + s))::uuid END,
                   0,
                   'Bench message ' || c || '/' || a || '/' || s,
                   md5('bench:course:' || c)::uuid,
                   md5('bench:asg:' || c || ':' || a)::uuid,
                   CASE WHEN s % 2 = 0 THEN md5('bench:sg:' || c || ':' || a || ':' || s)::uuid END,
                   timestamptz '2026-03-01 00:00:00+00'
                     + (((c * {assignments} + a) * {students} + s) * interval '1 second')
            FROM generate_series(0, {COURSES - 1}) c,
                 generate_series(0, {assignments - 1}) a,
                 generate_series(0, {students - 1}) s
            WHERE s % 8 = 0;
        """),
        ("message_read", f"""
            INSERT INTO message_read (id, message_id, reader_user_id)
            SELECT md5('bench:mr:' || c || ':' || a || ':' || s)::uuid,
                   md5('bench:msg:' || c || ':' || a || ':' || s)::uuid,
                   md5('bench:user:0')::uuid
            FROM generate_series(0, {COURSES - 1}) c,
                 generate_series(0, {assignments - 1}) a,
                 generate_series(0, {students - 1}) s
            WHERE s % 8 = 0 AND a % 3 = 0;
        """),
    ]


def truncate_data(cur) -> None:
    """Empty the generated tables, leaving the reference rows the migrations seeded."""
    cur.execute("""
        TRUNCATE message_read, message, result, submission_grade, submission_artifact,
                 submission_group_member, submission_group, course_content,
                 course_content_type, student_profile, course_member, course_group,
                 course, course_family, organization, profile, "user"
        RESTART IDENTITY CASCADE;
    """)


def seed(students: int, assignments: int) -> None:
    conn = psycopg2.connect(**_conn_params(BENCH_DB))
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            truncate_data(cur)
            for label, statement in build_steps(students, assignments):
                started = time.monotonic()
                cur.execute(statement)
                print(f"  {label:<38} {cur.rowcount:>9,} rows  ({time.monotonic() - started:.1f}s)")
        conn.commit()
        conn.autocommit = True
        with conn.cursor() as cur:
            print("  ANALYZE ...")
            cur.execute("ANALYZE;")
    finally:
        conn.close()


def report(cur) -> None:
    cur.execute("""
        SELECT relname, n_live_tup, pg_size_pretty(pg_total_relation_size(relid))
        FROM pg_stat_user_tables WHERE n_live_tup > 0
        ORDER BY n_live_tup DESC LIMIT 12;
    """)
    print("\n  largest tables")
    for name, rows, size in cur.fetchall():
        print(f"    {name:<28} {rows:>10,}  {size}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--scale", type=float, default=1.0,
                        help="multiplier on students and assignments (default 1.0)")
    parser.add_argument("--students", type=int, default=500,
                        help="students per course at scale 1 (default 500)")
    parser.add_argument("--assignments", type=int, default=60,
                        help="assignments per course at scale 1 (default 60)")
    parser.add_argument("--keep-schema", action="store_true",
                        help="reuse the existing bench database instead of recreating it")
    args = parser.parse_args()

    if not os.environ.get("POSTGRES_USER"):
        print("POSTGRES_USER is unset — run this with the repo .env sourced:\n"
              "  set -a; source .env; set +a", file=sys.stderr)
        return 2

    students = max(1, int(args.students * args.scale))
    assignments = max(1, int(args.assignments * args.scale))

    print(f"Seeding {BENCH_DB}: {COURSES} courses x {students} students x {assignments} assignments")
    started = time.monotonic()

    if not args.keep_schema:
        recreate_database()
        run_migrations()

    seed(students, assignments)

    conn = psycopg2.connect(**_conn_params(BENCH_DB))
    try:
        with conn.cursor() as cur:
            report(cur)
    finally:
        conn.close()

    print(f"\nDone in {time.monotonic() - started:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
