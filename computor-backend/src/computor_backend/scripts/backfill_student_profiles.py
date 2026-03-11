#!/usr/bin/env python3
"""
Backfill missing StudentProfile records for existing course members.

Course members created via the import endpoint before the post-create logic
was unified may be missing StudentProfile records. This script detects and
creates them.

A user can have multiple StudentProfiles — one per organization.

Usage:
    # Via environment variables (POSTGRES_HOST, POSTGRES_PORT, etc.):
    python backfill_student_profiles.py             # Dry run (default)
    python backfill_student_profiles.py --apply      # Create missing profiles

    # Via explicit database URL:
    python backfill_student_profiles.py --database-url postgresql+psycopg2://user:pass@host:5432/dbname
    python backfill_student_profiles.py --database-url postgresql+psycopg2://user:pass@host:5432/dbname --apply
"""

import json
import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from model.auth import User, StudentProfile
from model.course import CourseMember, Course


def _create_session(database_url: str | None = None) -> Session:
    """Create a database session.

    Args:
        database_url: Explicit database URL. If None, uses POSTGRES_* env vars
                      via the standard get_db() helper.

    Returns:
        Database session
    """
    if database_url:
        engine = create_engine(database_url)
        session_factory = sessionmaker(
            bind=engine,
            autocommit=False,
            expire_on_commit=False,
            autoflush=False,
        )
        return session_factory()

    # Fall back to standard get_db() which reads POSTGRES_* env vars
    from database import get_db
    return next(get_db())


def find_missing_profiles(db: Session) -> list[dict]:
    """
    Find all (user_id, organization_id) pairs that have a CourseMember
    but no corresponding StudentProfile.

    Excludes:
    - Service accounts (User.is_service == True)
    - Courses without an organization_id

    Returns:
        List of dicts with user_id, email, organization_id
    """
    # Subquery: existing (user_id, organization_id) pairs in student_profile
    existing_profiles = (
        db.query(
            StudentProfile.user_id,
            StudentProfile.organization_id,
        )
        .subquery()
    )

    # Find distinct (user_id, organization_id) from course_member + course
    # where no student_profile exists
    missing = (
        db.query(
            CourseMember.user_id,
            User.email,
            Course.organization_id,
        )
        .join(User, User.id == CourseMember.user_id)
        .join(Course, Course.id == CourseMember.course_id)
        .outerjoin(
            existing_profiles,
            (existing_profiles.c.user_id == CourseMember.user_id)
            & (existing_profiles.c.organization_id == Course.organization_id),
        )
        .filter(
            Course.organization_id.isnot(None),
            User.is_service == False,  # noqa: E712
            existing_profiles.c.user_id.is_(None),
        )
        .distinct()
        .all()
    )

    return [
        {
            "user_id": row.user_id,
            "email": row.email,
            "organization_id": row.organization_id,
        }
        for row in missing
    ]


def backfill(db: Session, missing: list[dict], apply: bool) -> int:
    """Create missing StudentProfile records.

    Args:
        db: Database session
        missing: List of missing profile dicts from find_missing_profiles
        apply: If False, only report (dry run)

    Returns:
        Number of profiles created (or would be created in dry run)
    """
    if not apply:
        # Dry run: show JSON preview of what would be inserted
        preview = [
            {
                "user_id": str(entry["user_id"]),
                "student_email": entry["email"],
                "organization_id": str(entry["organization_id"]),
                "student_id": None,
            }
            for entry in missing
        ]
        print(json.dumps(preview, indent=2))
        return len(preview)

    created = 0
    for entry in missing:
        profile = StudentProfile(
            user_id=entry["user_id"],
            student_email=entry["email"],
            organization_id=entry["organization_id"],
            student_id=None,
        )
        db.add(profile)
        created += 1

    db.commit()
    return created


def main():
    parser = argparse.ArgumentParser(
        description="Backfill missing StudentProfile records"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually create the missing profiles (default is dry run)",
    )
    parser.add_argument(
        "--database-url",
        type=str,
        default=None,
        help="Database URL (e.g. postgresql+psycopg2://user:pass@host:5432/db). "
             "If not provided, uses POSTGRES_* environment variables.",
    )
    args = parser.parse_args()

    mode = "APPLY" if args.apply else "DRY RUN"
    print(f"\nStudentProfile Backfill ({mode})")
    print("=" * 60)

    db = _create_session(args.database_url)

    try:
        missing = find_missing_profiles(db)
        print(f"Found {len(missing)} missing StudentProfile(s)\n")

        if not missing:
            print("Nothing to do.")
            return 0

        created = backfill(db, missing, apply=args.apply)

        print()
        if args.apply:
            print(f"Created {created} StudentProfile(s)")
        else:
            print(f"Would create {created} StudentProfile(s)")
            print("Run with --apply to create them.")

        return 0

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
