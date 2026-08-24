#!/usr/bin/env python3
"""Time the backend's hot read queries against the synthetic bench database.

Each scenario calls the *real* function the API calls — not a hand-written
approximation of its SQL — so a rewrite that changes the emitted query is
measured end to end, ORM materialisation included. Caches are disabled
throughout: the point is the database, and a cache hit would hide it.

``POSTGRES_DB`` is pinned to the bench database before ``computor_backend``
is imported, because ``computor_backend.database`` builds its engine at import
time. Nothing here can reach the dev database.

Usage::

    set -a; source .env; set +a
    python scripts/bench/bench_queries.py                       # all scenarios
    python scripts/bench/bench_queries.py -k dashboard          # a subset
    python scripts/bench/bench_queries.py --explain             # plans, not timings
    python scripts/bench/bench_queries.py --json after.json --baseline before.json
"""

from __future__ import annotations

import argparse
import asyncio
import inspect
import json
import os
import statistics
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "computor-backend" / "src"))
sys.path.insert(0, str(REPO_ROOT / "computor-types" / "src"))

# Must happen before computor_backend.database is imported.
os.environ["POSTGRES_DB"] = os.environ.get("BENCH_DB", "computor_bench")
# The dashboard queries are slow enough pre-fix that the app's 30s default
# would abort them and report a failure instead of a number.
os.environ.setdefault("DB_STATEMENT_TIMEOUT_MS", "300000")

from sqlalchemy import text  # noqa: E402

from computor_backend.database import SessionLocal  # noqa: E402
from computor_backend.permissions.principal import Principal  # noqa: E402

BENCH_DB = os.environ["POSTGRES_DB"]

# Deterministic ids from seed_bench_db.py — same md5 recipe, so the harness
# can address the seeded world without querying for handles first.
import hashlib  # noqa: E402


def bid(key: str) -> str:
    """The uuid ``md5('<key>')::uuid`` produces in the seeder."""
    h = hashlib.md5(key.encode()).hexdigest()
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


STUDENT_USER = bid("bench:user:0")
COURSE_0 = bid("bench:course:0")
ASSIGNMENT_0 = bid("bench:asg:0:0")


class Fixtures:
    """Ids resolved once from the seeded data.

    Only the student and course ids are derivable from the md5 recipe without
    knowing the scale; the tutor and lecturer indices shift with ``--students``,
    so those are looked up instead of recomputed.
    """

    def __init__(self, db):
        self.student_user_id = STUDENT_USER
        self.course_id = COURSE_0
        self.course_content_id = ASSIGNMENT_0

        row = db.execute(text("""
            SELECT cm.user_id, cm.id FROM course_member cm
            WHERE cm.course_id = :course AND cm.course_role_id = '_lecturer' LIMIT 1
        """), {"course": self.course_id}).first()
        self.lecturer_user_id, self.lecturer_member_id = str(row[0]), str(row[1])

        row = db.execute(text("""
            SELECT cm.user_id, cm.id FROM course_member cm
            WHERE cm.course_id = :course AND cm.course_role_id = '_tutor' LIMIT 1
        """), {"course": self.course_id}).first()
        self.tutor_user_id, self.tutor_member_id = str(row[0]), str(row[1])

        row = db.execute(text("""
            SELECT id FROM course_member
            WHERE course_id = :course AND user_id = :user
        """), {"course": self.course_id, "user": self.student_user_id}).first()
        self.student_member_id = str(row[0])

        self.course_group_id = str(db.execute(text(
            "SELECT id FROM course_group WHERE course_id = :course LIMIT 1"
        ), {"course": self.course_id}).scalar())


def student_principal(fx) -> Principal:
    return Principal(user_id=fx.student_user_id, roles=[])


def lecturer_principal(fx) -> Principal:
    return Principal(user_id=fx.lecturer_user_id, roles=[])


def tutor_principal(fx) -> Principal:
    return Principal(user_id=fx.tutor_user_id, roles=[])


# ---------------------------------------------------------------------------
# Scenarios
#
# Each returns a callable taking (db, fx). The return value is only used for
# the "rows" column, so returning a length or a list is equally fine.
# ---------------------------------------------------------------------------

SCENARIOS: dict[str, tuple[str, object]] = {}


def scenario(name: str, description: str):
    def register(fn):
        SCENARIOS[name] = (description, fn)
        return fn
    return register


@scenario("student_dashboard",
          "GET /students/course-contents — every assignment across the student's courses")
def _student_dashboard(db, fx):
    from computor_backend.repositories.course_content_queries import user_course_content_list_query
    return user_course_content_list_query(fx.student_user_id, db).all()


@scenario("student_dashboard_status_filter",
          "the same listing narrowed to one grading status")
def _student_dashboard_filtered(db, fx):
    from computor_backend.repositories.course_content_queries import user_course_content_list_query
    return user_course_content_list_query(fx.student_user_id, db, grading_statuses=[2]).all()


@scenario("student_course_content_detail",
          "GET /students/course-contents/{id} — the single-row variant")
def _student_detail(db, fx):
    from computor_backend.repositories.course_content_queries import user_course_content_query
    return [user_course_content_query(fx.student_user_id, fx.course_content_id, db)]


@scenario("latest_grade_subquery",
          "latest_submission_grade_status_subquery on its own")
def _latest_grade_subquery(db, fx):
    from computor_backend.repositories.course_content_subqueries import (
        latest_submission_grade_status_subquery,
    )
    sub = latest_submission_grade_status_subquery(db)
    return db.query(sub).all()


@scenario("my_submission_groups",
          "the submission groups one student belongs to")
def _my_submission_groups(db, fx):
    from computor_backend.model.course import SubmissionGroup, SubmissionGroupMember, CourseMember
    return (
        db.query(SubmissionGroup)
        .join(SubmissionGroupMember, SubmissionGroupMember.submission_group_id == SubmissionGroup.id)
        .join(CourseMember, CourseMember.id == SubmissionGroupMember.course_member_id)
        .filter(CourseMember.user_id == fx.student_user_id)
        .all()
    )


@scenario("tutor_submission_groups",
          "GET /tutors/submission-groups — one page of 100")
def _tutor_submission_groups(db, fx):
    from computor_backend.business_logic.tutor import list_tutor_submission_groups
    from computor_types.tutor_submission_groups import TutorSubmissionGroupQuery
    params = TutorSubmissionGroupQuery(course_id=fx.course_id, limit=100, offset=0)
    return list_tutor_submission_groups(lecturer_principal(fx), params, db, cache=None)


@scenario("tutor_submission_groups_ungraded",
          "the same page filtered to groups with ungraded submissions")
def _tutor_submission_groups_ungraded(db, fx):
    from computor_backend.business_logic.tutor import list_tutor_submission_groups
    from computor_types.tutor_submission_groups import TutorSubmissionGroupQuery
    params = TutorSubmissionGroupQuery(
        course_id=fx.course_id, limit=100, offset=0, has_ungraded_submissions=True
    )
    return list_tutor_submission_groups(lecturer_principal(fx), params, db, cache=None)


@scenario("visible_users",
          "the user list a lecturer may see (UserPermissionQueryBuilder)")
def _visible_users(db, fx):
    from computor_backend.permissions.query_builders import UserPermissionQueryBuilder
    q = UserPermissionQueryBuilder.filter_visible_users(fx.lecturer_user_id, db)
    q.count()  # the list endpoint counts before it pages
    return q.limit(100).all()


@scenario("course_member_list",
          "GET /course-members — the generic paginated list path")
def _course_member_list(db, fx):
    from computor_backend.business_logic.crud import list_entities
    from computor_backend.interfaces.course_member import CourseMemberInterface
    from computor_types.course_members import CourseMemberQuery
    params = CourseMemberQuery(course_id=fx.course_id, limit=100, skip=0)
    results, total = asyncio.run(
        list_entities(lecturer_principal(fx), db, params, CourseMemberInterface)
    )
    return results


@scenario("lecturer_course_contents",
          "GET /lecturers/course-contents — the content tree, cache disabled")
def _lecturer_course_contents(db, fx):
    from computor_backend.repositories.lecturer_view import LecturerViewRepository
    from computor_types.lecturer_course_contents import CourseContentLecturerQuery
    repo = LecturerViewRepository(cache=None)
    repo._db = db
    return repo.list_course_contents(
        lecturer_principal(fx), CourseContentLecturerQuery(course_id=fx.course_id)
    )


@scenario("artifacts_with_latest_result",
          "GET /submissions/artifacts?with_latest_result — one page of 100")
def _artifacts_with_latest_result(db, fx):
    from computor_backend.api.submissions import list_submission_artifacts
    from computor_types.artifacts import SubmissionArtifactQuery
    params = SubmissionArtifactQuery(limit=100, skip=0)

    class _Response:
        headers: dict = {}

    return asyncio.run(list_submission_artifacts(
        response=_Response(),
        permissions=lecturer_principal(fx),
        params=params,
        course_content_id=fx.course_content_id,
        with_latest_result=True,
        db=db,
    ))


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def measure(fn, fx, iterations: int, warmup: int) -> dict:
    """Run one scenario, on a fresh session per iteration.

    A fresh session per iteration keeps SQLAlchemy's identity map from turning
    the second run into a no-op — the first run would otherwise be the only
    honest one.
    """
    rows = 0
    for _ in range(warmup):
        db = SessionLocal()
        try:
            fn(db, fx)
        finally:
            db.close()

    samples: list[float] = []
    for _ in range(iterations):
        db = SessionLocal()
        try:
            started = time.perf_counter()
            out = fn(db, fx)
            samples.append((time.perf_counter() - started) * 1000.0)
            rows = len(out) if hasattr(out, "__len__") else 1
        finally:
            db.close()

    samples.sort()
    return {
        "rows": rows,
        "mean_ms": statistics.fmean(samples),
        "p50_ms": statistics.median(samples),
        "p95_ms": samples[min(len(samples) - 1, int(len(samples) * 0.95))],
        "min_ms": samples[0],
        "iterations": iterations,
    }


def count_queries(fn, fx) -> int:
    """How many statements one run of the scenario issues.

    The N+1 findings are about statement *count*, which a wall-clock number
    only shows indirectly — a loop of 600 fast queries can look acceptable on
    a warm local socket and be ruinous over a real network.
    """
    from sqlalchemy import event

    db = SessionLocal()
    counter = {"n": 0}

    def _on_execute(conn, cursor, statement, parameters, context, executemany):
        counter["n"] += 1

    event.listen(db.bind, "before_cursor_execute", _on_execute)
    try:
        fn(db, fx)
    finally:
        event.remove(db.bind, "before_cursor_execute", _on_execute)
        db.close()
    return counter["n"]


def explain(fn, fx) -> list[str]:
    """Capture EXPLAIN (ANALYZE, BUFFERS) for every statement the scenario runs.

    Only statements taking at least 1 ms are kept: a scenario can issue dozens
    of trivial lookups and their plans bury the one that matters.
    """
    from sqlalchemy import event

    plans: list[str] = []
    db = SessionLocal()
    seen: set[str] = set()

    def _on_execute(conn, cursor, statement, parameters, context, executemany):
        if executemany or not statement.lstrip().upper().startswith("SELECT"):
            return
        if statement in seen:
            return
        seen.add(statement)
        try:
            side = SessionLocal()
            try:
                rows = side.execute(
                    text("EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) " + statement), parameters
                ).fetchall()
            finally:
                side.close()
        except Exception as exc:  # a plan we cannot take is not a benchmark failure
            plans.append(f"-- EXPLAIN failed: {exc}")
            return
        body = "\n".join(r[0] for r in rows)
        if "Execution Time:" in body:
            ms = float(body.rsplit("Execution Time:", 1)[1].split("ms")[0])
            if ms < 1.0:
                return
        plans.append(body)

    event.listen(db.bind, "before_cursor_execute", _on_execute)
    try:
        fn(db, fx)
    finally:
        event.remove(db.bind, "before_cursor_execute", _on_execute)
        db.close()
    return plans


def _fmt_delta(before: float, after: float) -> str:
    if before <= 0:
        return "     —"
    change = (after - before) / before * 100.0
    if abs(change) < 1.0:
        return "    ~="
    return f"{change:+7.1f}%"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("-k", "--select", default=None,
                        help="only scenarios whose name contains this substring")
    parser.add_argument("-n", "--iterations", type=int, default=7)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--explain", action="store_true",
                        help="print query plans instead of timings")
    parser.add_argument("--json", dest="json_out", default=None,
                        help="write the results to this file")
    parser.add_argument("--baseline", default=None,
                        help="compare against a previous --json file")
    parser.add_argument("--list", action="store_true", help="list scenarios and exit")
    args = parser.parse_args()

    if args.list:
        for name, (desc, _) in SCENARIOS.items():
            print(f"  {name:<34} {desc}")
        return 0

    if not os.environ.get("POSTGRES_USER"):
        print("POSTGRES_USER is unset — run with the repo .env sourced:\n"
              "  set -a; source .env; set +a", file=sys.stderr)
        return 2

    selected = {
        name: entry for name, entry in SCENARIOS.items()
        if args.select is None or args.select in name
    }
    if not selected:
        print(f"no scenario matches {args.select!r}", file=sys.stderr)
        return 2

    db = SessionLocal()
    try:
        fx = Fixtures(db)
    finally:
        db.close()

    baseline = {}
    if args.baseline:
        baseline = json.loads(Path(args.baseline).read_text()).get("scenarios", {})

    print(f"database: {BENCH_DB}   iterations: {args.iterations}\n")

    if args.explain:
        for name, (desc, fn) in selected.items():
            print(f"\n{'=' * 78}\n{name} — {desc}\n{'=' * 78}")
            for plan in explain(fn, fx):
                print(plan)
                print("-" * 78)
        return 0

    header = f"{'scenario':<34} {'rows':>7} {'queries':>8} {'p50 ms':>10} {'p95 ms':>10}"
    if baseline:
        header += f" {'vs base':>9}"
    print(header)
    print("-" * len(header))

    results = {}
    for name, (desc, fn) in selected.items():
        queries = count_queries(fn, fx)
        stats = measure(fn, fx, args.iterations, args.warmup)
        stats["queries"] = queries
        stats["description"] = desc
        results[name] = stats

        line = (f"{name:<34} {stats['rows']:>7,} {queries:>8,} "
                f"{stats['p50_ms']:>10.1f} {stats['p95_ms']:>10.1f}")
        if baseline:
            prev = baseline.get(name)
            line += f" {_fmt_delta(prev['p50_ms'], stats['p50_ms']):>9}" if prev else f" {'new':>9}"
        print(line)

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(
            {"database": BENCH_DB, "scenarios": results}, indent=2
        ))
        print(f"\nwrote {args.json_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
