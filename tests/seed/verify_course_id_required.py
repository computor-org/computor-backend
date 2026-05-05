"""Verify /tutors/course-members and /tutors/submission-groups require course_id.

Calls the business logic directly (FastAPI not required) to check:
  1. Missing course_id raises BadRequestException
  2. Providing course_id still returns data correctly
"""
import os

os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_USER", "postgres")
os.environ.setdefault("POSTGRES_PASSWORD", "postgres_secret")
os.environ.setdefault("POSTGRES_DB", "codeability")

from sqlalchemy import text

from computor_backend.database import SessionLocal
from computor_backend.business_logic.tutor import (
    list_tutor_course_members,
    list_tutor_submission_groups,
)
from computor_backend.exceptions import BadRequestException
from computor_backend.permissions.principal import Principal, Claims
from computor_types.course_members import CourseMemberQuery
from computor_types.tutor_submission_groups import TutorSubmissionGroupQuery


COURSE_ID = "2fc15de7-40a7-4e85-b633-448823184684"


def make_principal(user_id: str, is_admin: bool = False) -> Principal:
    return Principal(
        is_admin=is_admin,
        user_id=user_id,
        roles=[],
        claims=Claims(general={}, dependent={}),
        permissions={},
    )


def assert_raises(fn, exc_type):
    try:
        fn()
    except exc_type as e:
        return e
    except Exception as e:
        raise AssertionError(f"Expected {exc_type.__name__}, got {type(e).__name__}: {e}")
    raise AssertionError(f"Expected {exc_type.__name__}, no exception raised")


def main():
    with SessionLocal() as db:
        row = db.execute(text("""
            SELECT cm.user_id
            FROM course_member cm
            JOIN "user" u ON u.id = cm.user_id
            WHERE cm.course_role_id = '_tutor'
              AND cm.course_id = :cid
              AND u.username LIKE 'bench_%%'
            ORDER BY u.created_at DESC LIMIT 1
        """), {"cid": COURSE_ID}).first()
        if not row:
            print("No benchmark tutor found. Run seed_tutor_benchmark.sql first.")
            return
        tutor_user_id = str(row.user_id)

    principal = make_principal(tutor_user_id)

    # --- list_tutor_course_members ---
    print("1. list_tutor_course_members without course_id -> expect 400")
    with SessionLocal() as db:
        err = assert_raises(
            lambda: list_tutor_course_members(principal, CourseMemberQuery(), db),
            BadRequestException,
        )
        print(f"   raised: {err.detail!r}")

    print("2. list_tutor_course_members WITH course_id -> expect data")
    with SessionLocal() as db:
        result = list_tutor_course_members(
            principal, CourseMemberQuery(course_id=COURSE_ID), db
        )
        print(f"   got {len(result)} members")
        assert len(result) > 0, "expected members"

    # --- list_tutor_submission_groups ---
    print("3. list_tutor_submission_groups without course_id -> expect 400")
    with SessionLocal() as db:
        err = assert_raises(
            lambda: list_tutor_submission_groups(principal, TutorSubmissionGroupQuery(), db),
            BadRequestException,
        )
        print(f"   raised: {err.detail!r}")

    print("4. list_tutor_submission_groups WITH course_id -> expect data")
    with SessionLocal() as db:
        result = list_tutor_submission_groups(
            principal, TutorSubmissionGroupQuery(course_id=COURSE_ID), db
        )
        print(f"   got {len(result)} submission groups")
        assert len(result) > 0, "expected submission groups"

    # --- admin also blocked ---
    print("5. Admin without course_id is also blocked")
    admin = make_principal(tutor_user_id, is_admin=True)
    with SessionLocal() as db:
        err = assert_raises(
            lambda: list_tutor_course_members(admin, CourseMemberQuery(), db),
            BadRequestException,
        )
        print(f"   raised: {err.detail!r}")

    print("\nAll assertions passed.")


if __name__ == "__main__":
    main()
