#!/usr/bin/env python3
"""Put existing self-enrolled learners into the ``Selbsteinschreibung`` group.

New self-enrolments land in that group on join (issues#458). Run this once
after deploying that change to move the learners who joined earlier. It is a
dry run unless ``--apply`` is given, and a second run finds nothing to move.

Usage (database from the POSTGRES_* environment variables):
    python -m computor_backend.scripts.backfill_self_enrollment_group
    python -m computor_backend.scripts.backfill_self_enrollment_group --apply
"""

import argparse
from collections import Counter

from computor_backend.business_logic.course_registration import (
    SELF_REGISTRATION_GROUP_TITLE,
    assign_self_enrolled_to_group,
)
from computor_backend.database import get_db


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="write the changes")
    args = parser.parse_args()

    db = next(get_db())
    try:
        moves = assign_self_enrolled_to_group(db, apply=args.apply)
    finally:
        db.close()

    per_course = Counter(move["course_id"] for move in moves)
    for course_id, count in sorted(per_course.items()):
        print(f"course {course_id}: {count} learner(s)")
    verb = "Moved" if args.apply else "Would move"
    print(f"{verb} {len(moves)} learner(s) in {len(per_course)} course(s) "
          f"into '{SELF_REGISTRATION_GROUP_TITLE}'.")
    if not args.apply and moves:
        print("Dry run; nothing was written. Re-run with --apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
