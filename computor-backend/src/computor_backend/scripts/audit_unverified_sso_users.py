#!/usr/bin/env python3
"""
Count users whose email came from an SSO login the IdP had not verified.

Before the email_verified guard in business_logic.auth.handle_sso_callback, a
first SSO login created (or linked) a User owning whatever email the token
carried, verified or not. Such a user may hold someone else's address, and a
staff import by that email would enrol them in the owner's place.

Read-only. Prints counts only, never emails or ids, so the output can go into
a ticket. A user is counted when it has an email and none of its SSO identity
accounts (``Account.builtin``) recorded ``email_verified: true`` at its last
login. ``handle_sso_callback`` stores the claim in
``Account.properties["attributes"]`` on every login, so "missing" means the
account predates that or the IdP sent no claim.

Usage:
    # Via environment variables (POSTGRES_HOST, POSTGRES_PORT, etc.):
    python audit_unverified_sso_users.py
    # Via explicit database URL:
    python audit_unverified_sso_users.py --database-url postgresql+psycopg2://user:pass@host:5432/dbname

Follow-up for each counted user is a human decision (confirm the address with
the person, then fix User.email or archive the user); this script changes
nothing.
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session, sessionmaker


def _create_session(database_url: str | None = None) -> Session:
    if database_url:
        return sessionmaker(bind=create_engine(database_url))()
    from computor_backend.database import get_db

    return next(get_db())


def audit(db: Session) -> dict[str, int]:
    """Counts of email-bearing users with no verified SSO identity."""
    from computor_backend.model.auth import Account, User
    from computor_backend.model.course import CourseMember

    verified_flag = Account.properties["attributes"]["email_verified"]
    rows = (
        db.query(Account.user_id, verified_flag.astext)
        .join(User, User.id == Account.user_id)
        .filter(Account.builtin.is_(True), User.email.isnot(None))
        .all()
    )

    verified: set[str] = set()
    explicit_false: set[str] = set()
    missing: set[str] = set()
    for user_id, flag in rows:
        uid = str(user_id)
        if flag == "true":
            verified.add(uid)
        elif flag is None:
            missing.add(uid)
        else:
            explicit_false.add(uid)

    unverified = (explicit_false | missing) - verified
    explicit_false -= verified
    missing -= verified | explicit_false

    with_membership = 0
    if unverified:
        with_membership = (
            db.query(func.count(func.distinct(CourseMember.user_id)))
            .filter(CourseMember.user_id.in_(unverified))
            .scalar()
        )

    return {
        "sso_users_with_email": len(verified | unverified),
        "unverified_total": len(unverified),
        "unverified_email_verified_false": len(explicit_false),
        "unverified_claim_missing": len(missing),
        "unverified_with_course_membership": with_membership,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--database-url", default=None)
    args = parser.parse_args()

    db = _create_session(args.database_url)
    try:
        for key, value in audit(db).items():
            print(f"{key}: {value}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
