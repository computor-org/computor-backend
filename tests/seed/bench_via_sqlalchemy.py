"""Run the actual list_tutor_course_members flow and print timings + SQL.

Usage:
    python tests/seed/bench_via_sqlalchemy.py
"""
import os
import time
import statistics
from uuid import UUID

os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_USER", "postgres")
os.environ.setdefault("POSTGRES_PASSWORD", "postgres_secret")
os.environ.setdefault("POSTGRES_DB", "codeability")

from sqlalchemy import text, event
from sqlalchemy.engine import Engine

from computor_backend.database import SessionLocal
from computor_backend.business_logic.tutor import list_tutor_course_members
from computor_backend.permissions.principal import Principal, Claims
from computor_types.course_members import CourseMemberQuery


COURSE_ID = "2fc15de7-40a7-4e85-b633-448823184684"


def find_tutor():
    with SessionLocal() as db:
        row = db.execute(text("""
            SELECT cm.id, cm.user_id
            FROM course_member cm
            JOIN "user" u ON u.id = cm.user_id
            WHERE cm.course_role_id = '_tutor'
              AND cm.course_id = :cid
              AND u.username LIKE 'bench_%%'
            ORDER BY u.created_at DESC
            LIMIT 1
        """), {"cid": COURSE_ID}).first()
        return str(row.user_id) if row else None


def build_tutor_principal(user_id: str) -> Principal:
    return Principal(
        is_admin=False,
        user_id=user_id,
        roles=[],
        claims=Claims(general={}, dependent={}),
        permissions={},
    )


def time_call(principal, params, n=3, cache=None):
    timings = []
    # first call is the cold one; also include a warm cache call to see the diff
    with SessionLocal() as db:
        for _ in range(n):
            t0 = time.perf_counter()
            result = list_tutor_course_members(principal, params, db, cache=cache)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            timings.append(elapsed_ms)
    return timings, len(result)


def capture_sql(principal, params):
    statements = []
    start_map = {}

    @event.listens_for(Engine, "before_cursor_execute")
    def _before(conn, cursor, statement, parameters, context, executemany):
        start_map[id(context)] = time.perf_counter()

    @event.listens_for(Engine, "after_cursor_execute")
    def _after(conn, cursor, statement, parameters, context, executemany):
        t0 = start_map.pop(id(context), None)
        elapsed_ms = (time.perf_counter() - t0) * 1000 if t0 else None
        statements.append((statement, parameters, elapsed_ms))

    try:
        with SessionLocal() as db:
            list_tutor_course_members(principal, params, db, cache=None)
    finally:
        event.remove(Engine, "before_cursor_execute", _before)
        event.remove(Engine, "after_cursor_execute", _after)
    return statements


def main():
    tutor_user_id = find_tutor()
    if not tutor_user_id:
        print("No benchmark tutor found. Run seed_tutor_benchmark.sql first.")
        return

    print(f"Using tutor user_id = {tutor_user_id}")

    principal = build_tutor_principal(tutor_user_id)
    params = CourseMemberQuery(course_id=COURSE_ID)

    print("\n=== No cache (always hits DB) ===")
    timings, n_rows = time_call(principal, params, n=5, cache=None)
    print(f"Rows returned: {n_rows}")
    print(f"Call latencies (ms): {['%.1f' % t for t in timings]}")
    print(f"  mean={statistics.mean(timings):.1f}  median={statistics.median(timings):.1f}")

    # Now with real Redis cache
    from computor_backend.redis_cache import get_cache
    cache = get_cache()
    # Flush the specific cache tag first
    cache.invalidate_tags(f"tutor_view:{COURSE_ID}")
    print("\n=== With Redis cache (first call cold, rest warm) ===")
    timings, n_rows = time_call(principal, params, n=5, cache=cache)
    print(f"Rows returned: {n_rows}")
    print(f"Call latencies (ms): {['%.1f' % t for t in timings]}")
    print(f"  mean={statistics.mean(timings):.1f}  median={statistics.median(timings):.1f}")

    print("\n--- SQL statements emitted for a single call (with timings) ---")
    stmts = capture_sql(principal, params)
    for i, (s, p, ms) in enumerate(stmts, 1):
        first_line = s.strip().splitlines()[0][:100]
        print(f"{i:2d}. {ms:7.1f} ms  {first_line}")
    print(f"   ({len(stmts)} statements, {sum(m for _,_,m in stmts):.1f} ms total)")

    # Dump the slowest statement in full so we can EXPLAIN it
    slowest = max(stmts, key=lambda x: x[2])
    print("\n--- Slowest statement (full SQL) ---")
    print(slowest[0])
    print("--- Params ---")
    print(slowest[1])


if __name__ == "__main__":
    main()
