#!/usr/bin/env python3
"""Development seeder — enrols fake users into existing courses (real mechanics).

Builds an admin ``Principal`` and calls the backend's own
``import_course_member`` for each fake user — the exact code path the API uses —
so every mechanic runs: the user is found-or-created, a StudentProfile is
ensured, submission groups are provisioned, and (for legacy-git courses) the
repository workflow is triggered. A raw INSERT skips all of that, which is why
directly-inserted members misbehave.

In-process, so it needs Postgres up (`startup.sh`) but NOT the API (`api.sh`) or
Keycloak. Fake users (email ``dev.userNNN@seed.local``) are not loginable.
Idempotent: users are found-or-created by email and the import updates an
existing member instead of duplicating.

Usage (via the wrapper, which activates the venv):
    bash seed.sh                       # 20 users into every course
    bash seed.sh --users 50            # 50 users per course
    bash seed.sh --course-id <uuid>    # only that course
    bash seed.sh --course-path <ltree> # only the course at that path
    bash seed.sh --cleanup-only        # delete seeded users (memberships cascade)
    bash seed.sh --cleanup             # delete seeded, then reseed
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except Exception:
    pass

for _src in (ROOT / "computor-backend" / "src", ROOT / "computor-types" / "src"):
    if _src.is_dir() and str(_src) not in sys.path:
        sys.path.insert(0, str(_src))

SEED_EMAIL_DOMAIN = "seed.local"
ADMIN_EMAIL = os.environ.get("API_ADMIN_EMAIL", "admin@computor.local")


def get_session():
    from computor_backend.database import SessionLocal

    return SessionLocal()


def admin_principal(db):
    """An admin Principal so the import bypasses course-membership checks and can
    seat any role. Uses the bootstrap admin's id for created_by when present."""
    from computor_backend.model.auth import User
    from computor_backend.permissions.principal import Principal

    admin = db.query(User).filter(User.email == ADMIN_EMAIL).first()
    return Principal(
        is_admin=True,
        user_id=str(admin.id) if admin else None,
        roles=["_admin"],
    )


def role_for_index(i, lecturers, tutors):
    if i < lecturers:
        return "_lecturer"
    if i < lecturers + tutors:
        return "_tutor"
    return "_student"


async def _seed_course(db, principal, course, users_n, lecturers, tutors, fake):
    from computor_backend.business_logic.course_member_import import import_course_member
    from computor_types.course_member_import import CourseMemberImportRequest

    ok = fail = 0
    for i in range(users_n):
        role = role_for_index(i, lecturers, tutors)
        request = CourseMemberImportRequest(
            email=f"dev.user{i:03d}@{SEED_EMAIL_DOMAIN}",
            given_name=fake.first_name() if fake else f"Dev{i:03d}",
            family_name=fake.last_name() if fake else "Seed",
            course_role_id=role,
            # Students must belong to a group (DB constraint); the import
            # creates it on demand from this title.
            course_group_title="Seed Group" if role == "_student" else None,
            create_missing_group=True,
        )
        try:
            resp = await import_course_member(str(course.id), request, principal, db)
            if resp.success:
                db.commit()
                ok += 1
            else:
                db.rollback()
                fail += 1
                if fail <= 3:
                    print(f"    ! {request.email}: {resp.message}")
        except Exception as exc:  # keep going; one bad row shouldn't abort the run
            db.rollback()
            fail += 1
            if fail <= 3:
                print(f"    ! {request.email}: {exc}")
    return ok, fail


async def _seed(db, principal, courses, users_n, lecturers, tutors):
    try:
        from faker import Faker

        fake = Faker()
    except ImportError:
        fake = None

    total_ok = total_fail = 0
    for course in courses:
        ok, fail = await _seed_course(db, principal, course, users_n, lecturers, tutors, fake)
        print(f"  {course.title or course.path}: {ok} enrolled, {fail} failed")
        total_ok += ok
        total_fail += fail

    print(f"\nDone: {total_ok} enrolments ok, {total_fail} failed across {len(courses)} course(s).")
    return total_fail == 0


def seed(course_path, course_id, users_n, lecturers, tutors):
    from computor_backend.model.course import Course
    from computor_backend.custom_types import Ltree

    db = get_session()
    try:
        query = db.query(Course)
        if course_id:
            query = query.filter(Course.id == course_id)
        elif course_path:
            query = query.filter(Course.path == Ltree(course_path))
        courses = query.all()

        if not courses:
            print("No matching courses found. Create a course first.")
            return False

        principal = admin_principal(db)
        return asyncio.run(_seed(db, principal, courses, users_n, lecturers, tutors))
    finally:
        db.close()


def cleanup():
    """Delete seeded users (email @seed.local); their memberships cascade at the
    DB level. Also drop the auto-created 'Seed Group's once they're empty."""
    from computor_backend.model.auth import User
    from computor_backend.model.course import CourseMember, CourseGroup

    db = get_session()
    try:
        ids = [row[0] for row in db.query(User.id).filter(User.email.ilike(f"%@{SEED_EMAIL_DOMAIN}")).all()]
        n_members = (
            db.query(CourseMember).filter(CourseMember.user_id.in_(ids)).count() if ids else 0
        )
        n_users = (
            db.query(User).filter(User.id.in_(ids)).delete(synchronize_session=False) if ids else 0
        )
        db.flush()

        empty_seed_groups = (
            db.query(CourseGroup)
            .filter(CourseGroup.title == "Seed Group", ~CourseGroup.course_members.any())
            .all()
        )
        n_groups = len(empty_seed_groups)
        for group in empty_seed_groups:
            db.delete(group)

        db.commit()
        print(
            f"Cleanup: deleted {n_users} users ({n_members} memberships cascade), "
            f"{n_groups} empty groups."
        )
        return True
    except Exception:
        db.rollback()
        import traceback

        traceback.print_exc()
        return False
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Seed dev users into existing courses via the real import logic."
    )
    parser.add_argument("--users", type=int, default=20, help="Users per course (default 20).")
    parser.add_argument("--lecturers", type=int, default=1, help="Lecturers per course (default 1).")
    parser.add_argument("--tutors", type=int, default=2, help="Tutors per course (default 2).")
    parser.add_argument("--course-path", default=None, help="Only seed the course at this Ltree path.")
    parser.add_argument("--course-id", default=None, help="Only seed the course with this id.")
    parser.add_argument("--cleanup", action="store_true", help="Remove seeded users before seeding.")
    parser.add_argument("--cleanup-only", action="store_true", help="Only remove seeded users.")
    args = parser.parse_args()

    if args.cleanup or args.cleanup_only:
        if not cleanup():
            sys.exit(1)
        if args.cleanup_only:
            return

    if not seed(args.course_path, args.course_id, args.users, args.lecturers, args.tutors):
        sys.exit(1)


if __name__ == "__main__":
    main()
