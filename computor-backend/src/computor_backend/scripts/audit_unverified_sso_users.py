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
login *for that same address* (a verified login under another address does
not count). ``handle_sso_callback`` stores the claim in
``Account.properties["attributes"]`` and the address in
``Account.properties["email"]`` on every login, so "missing" means the
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


def _normalize(email) -> str | None:
    if not isinstance(email, str):
        return None
    return email.strip().lower() or None


def classify(user_email: str, accounts: list[dict | None]) -> str:
    """How well a user's SSO accounts vouch for ``User.email``.

    ``verified`` only when some account's last login carried
    ``email_verified`` as boolean ``true`` *for that same address*. A verified
    login under a different address says nothing about ``User.email``: a
    pre-fix login could reserve someone else's unverified address and later
    log in with its own verified one, while User.email kept the reservation.
    Otherwise the strongest evidence wins: ``mismatch`` (verified, other
    address), then ``false`` (claim false or non-boolean), then ``missing``.
    """
    target = _normalize(user_email)
    seen = set()
    for properties in accounts:
        properties = properties or {}
        flag = (properties.get("attributes") or {}).get("email_verified", None)
        if flag is True:
            if _normalize(properties.get("email")) == target:
                return "verified"
            seen.add("mismatch")
        elif "email_verified" in (properties.get("attributes") or {}):
            seen.add("false")
        else:
            seen.add("missing")
    for label in ("mismatch", "false", "missing"):
        if label in seen:
            return label
    return "missing"


def audit(db: Session) -> dict[str, int]:
    """Counts of email-bearing SSO users whose User.email is not verified."""
    from computor_backend.model.auth import Account, User
    from computor_backend.model.course import CourseMember

    rows = (
        db.query(User.id, User.email, Account.properties)
        .join(Account, Account.user_id == User.id)
        .filter(Account.builtin.is_(True), User.email.isnot(None))
        .all()
    )
    by_user: dict[str, tuple[str, list]] = {}
    for user_id, email, properties in rows:
        by_user.setdefault(str(user_id), (email, []))[1].append(properties)

    labels = {uid: classify(email, props) for uid, (email, props) in by_user.items()}
    unverified = {uid for uid, label in labels.items() if label != "verified"}

    with_membership = 0
    if unverified:
        with_membership = (
            db.query(func.count(func.distinct(CourseMember.user_id)))
            .filter(CourseMember.user_id.in_(unverified))
            .scalar()
        )

    def _count(label: str) -> int:
        return sum(1 for value in labels.values() if value == label)

    return {
        "sso_users_with_email": len(labels),
        "unverified_total": len(unverified),
        "unverified_verified_other_email": _count("mismatch"),
        "unverified_email_verified_false": _count("false"),
        "unverified_claim_missing": _count("missing"),
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
