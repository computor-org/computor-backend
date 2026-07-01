#!/usr/bin/env python3
"""Development database seeder — fake users enrolled into existing courses.

Creates a pool of fake users and enrols them into EXISTING courses with a role
mix (a few lecturers/tutors, the rest students), so you have realistic rosters
to work with in the web UI and the VS Code extension.

Direct-DB only: it does NOT create Keycloak accounts, Forgejo repos, or student
profiles (the API's post-create hook is bypassed). Seeded users therefore show
up in ``/users`` and in course rosters but cannot SSO-log-in — this is a data
seeder for UI/roster/analytics work, not a way to mint login accounts.

Every row it writes is tagged ``properties.dev_seed = true`` so ``--cleanup``
removes exactly what was seeded and nothing else. It is idempotent: users are
found-or-created by a stable email and existing memberships are skipped, so
re-running never duplicates.

Usage (prefer the wrapper, which activates the venv):
    bash seed.sh                        # 20 users into every course
    bash seed.sh --users 50             # 50 users per course
    bash seed.sh --course-path py-2025  # only the course at that path
    bash seed.sh --cleanup              # remove seeded rows, then reseed
    bash seed.sh --cleanup-only         # just remove seeded rows
"""

import argparse
import sys
import uuid
from pathlib import Path

# scripts/ -> computor_backend -> src -> computor-backend -> repo root
ROOT = Path(__file__).resolve().parents[4]

# Load the repo .env so SessionLocal picks up the dev datastore config.
_env_file = ROOT / ".env"
if _env_file.exists():
    try:
        from dotenv import load_dotenv

        load_dotenv(_env_file)
    except ImportError:
        pass

# Make the backend + types importable when run outside an installed env.
for _src in (ROOT / "computor-backend" / "src", ROOT / "computor-types" / "src"):
    if _src.is_dir() and str(_src) not in sys.path:
        sys.path.insert(0, str(_src))

DEV_SEED_TAG = "dev_seed"
DEV_EMAIL_DOMAIN = "seed.local"


def get_session():
    from computor_backend.database import SessionLocal

    return SessionLocal()


def create_users(db, count):
    """Find-or-create `count` users by a stable email (idempotent)."""
    from computor_backend.model.auth import User

    try:
        from faker import Faker

        fake = Faker()
    except ImportError:
        fake = None

    users = []
    created = 0
    for i in range(count):
        email = f"dev.user{i:03d}@{DEV_EMAIL_DOMAIN}"
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            user = User(
                id=str(uuid.uuid4()),
                given_name=fake.first_name() if fake else f"Dev{i:03d}",
                family_name=fake.last_name() if fake else "Seed",
                email=email,
                properties={DEV_SEED_TAG: True},
            )
            db.add(user)
            created += 1
        users.append(user)
    db.flush()
    print(f"Users: {created} created, {len(users) - created} reused ({len(users)} total).")
    return users


def ensure_group(db, course):
    """Return a course group for students, creating one if the course has none."""
    from computor_backend.model.course import CourseGroup

    group = (
        db.query(CourseGroup)
        .filter(CourseGroup.course_id == course.id)
        .order_by(CourseGroup.created_at)
        .first()
    )
    if group is not None:
        return group

    group = CourseGroup(
        id=str(uuid.uuid4()),
        course_id=str(course.id),
        title="Seed Group",
        description="Auto-created by seed_dev.py",
        properties={DEV_SEED_TAG: True},
    )
    db.add(group)
    db.flush()
    return group


def role_for_index(i, lecturers, tutors):
    if i < lecturers:
        return "_lecturer"
    if i < lecturers + tutors:
        return "_tutor"
    return "_student"


def enrol(db, course, users, lecturers, tutors):
    """Add users to a course with a role mix; skip users already enrolled.

    Students must belong to a course group (DB CheckConstraint), so a group is
    ensured lazily the first time a student is added.
    """
    from computor_backend.model.course import CourseMember

    existing_user_ids = {
        str(row[0])
        for row in db.query(CourseMember.user_id)
        .filter(CourseMember.course_id == course.id)
        .all()
    }

    group = None
    created = 0
    for i, user in enumerate(users):
        if str(user.id) in existing_user_ids:
            continue
        role = role_for_index(i, lecturers, tutors)
        group_id = None
        if role == "_student":
            if group is None:
                group = ensure_group(db, course)
            group_id = str(group.id)
        db.add(
            CourseMember(
                id=str(uuid.uuid4()),
                user_id=str(user.id),
                course_id=str(course.id),
                course_role_id=role,
                course_group_id=group_id,
                properties={DEV_SEED_TAG: True},
            )
        )
        created += 1
    db.flush()
    return created


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

        users = create_users(db, users_n)

        total = 0
        for course in courses:
            added = enrol(db, course, users, lecturers, tutors)
            total += added
            print(f"  {course.title or course.path}: +{added} members")

        db.commit()
        print(
            f"\nDone: {len(users)} users, {total} new memberships across "
            f"{len(courses)} course(s)."
        )
        return True
    except Exception:
        db.rollback()
        import traceback

        traceback.print_exc()
        return False
    finally:
        db.close()


def cleanup():
    """Delete every row tagged ``properties.dev_seed`` (members → groups → users)."""
    from computor_backend.model.auth import User
    from computor_backend.model.course import CourseMember, CourseGroup

    tag = {DEV_SEED_TAG: True}
    db = get_session()
    try:
        members = (
            db.query(CourseMember)
            .filter(CourseMember.properties.contains(tag))
            .delete(synchronize_session=False)
        )
        groups = (
            db.query(CourseGroup)
            .filter(CourseGroup.properties.contains(tag))
            .delete(synchronize_session=False)
        )
        users = (
            db.query(User)
            .filter(User.properties.contains(tag))
            .delete(synchronize_session=False)
        )
        db.commit()
        print(f"Cleanup: removed {users} users, {members} memberships, {groups} groups.")
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
        description="Seed dev users and enrol them into existing courses."
    )
    parser.add_argument("--users", type=int, default=20, help="Users to create (default 20).")
    parser.add_argument("--lecturers", type=int, default=1, help="Lecturers per course (default 1).")
    parser.add_argument("--tutors", type=int, default=2, help="Tutors per course (default 2).")
    parser.add_argument("--course-path", default=None, help="Only seed the course at this Ltree path.")
    parser.add_argument("--course-id", default=None, help="Only seed the course with this id.")
    parser.add_argument("--cleanup", action="store_true", help="Remove seeded rows before seeding.")
    parser.add_argument("--cleanup-only", action="store_true", help="Only remove seeded rows.")
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
