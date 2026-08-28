"""Who owns a course the moment it is created.

Whoever creates a course is enrolled in it as ``_owner`` (issue #386).
Creating a course is a global-permission act, but *managing* one is decided by
course membership, so without this the creator lands on a course they cannot
edit, assign examples in, or release — exactly what the issue reports.

The one exception is the deployment's bootstrap administrator (see
``utils.bootstrap_admin``). That identity is infrastructure rather than a
person: it already bypasses every permission check through ``_admin``, so the
membership buys it nothing, and it can never hold a git-server account, so the
row would only ever describe a course member whose repository cannot exist.
Note this is *not* "admins are skipped" — a human administrator who creates a
course is its owner like anyone else; only the single bootstrap account is not.

Every path that creates a course routes through here: the plain
``POST /courses`` (via ``CourseInterface.post_create``), the course-deployment
apply, and the hierarchy-creation Temporal activity.
"""

import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from computor_backend.model.course import CourseMember
from computor_backend.utils.bootstrap_admin import user_is_bootstrap_admin

logger = logging.getLogger(__name__)

OWNER_ROLE_ID = "_owner"


def enroll_course_creator_as_owner(
    course: Any,
    db: Session,
    user_id: Optional[Any] = None,
) -> Optional[CourseMember]:
    """Add the course's creator as ``_owner``, and return the new membership.

    ``user_id`` overrides ``course.created_by`` for callers that know the acting
    user directly (the Temporal activity gets it as an argument; the audit
    columns are only populated by the database trigger on the CRUD path).

    Returns ``None`` when nothing was written — no creator, the bootstrap
    admin, or a membership that already exists. Idempotent, so re-running a
    deployment over an existing course does not fail on the unique
    ``(user_id, course_id)`` index.

    Only flushes. The caller owns the transaction, and the CRUD path in
    particular runs this after its own commit, inside a session the request
    dependency commits on the way out.
    """
    if course is None:
        return None

    creator_id = user_id or getattr(course, "created_by", None)
    if not creator_id:
        return None

    if user_is_bootstrap_admin(creator_id, db):
        logger.info(
            "Not enrolling the bootstrap administrator as owner of course %s",
            course.id,
        )
        return None

    existing = (
        db.query(CourseMember)
        .filter(
            CourseMember.user_id == str(creator_id),
            CourseMember.course_id == str(course.id),
        )
        .first()
    )
    if existing is not None:
        return None

    member = CourseMember(
        user_id=str(creator_id),
        course_id=str(course.id),
        course_role_id=OWNER_ROLE_ID,
        created_by=str(creator_id),
        updated_by=str(creator_id),
    )
    db.add(member)
    db.flush()
    logger.info(
        "Auto-assigned creator %s as %s of course %s",
        creator_id,
        OWNER_ROLE_ID,
        course.id,
    )
    return member


def invalidate_creator_caches(user_id: str) -> None:
    """Drop the user-keyed caches that would hide the fresh membership.

    Two caches answer "what courses is this user in": the course-membership
    permission cache and the role-aware view cache. Both are keyed by user, so
    they can be dropped from anywhere. The third — the Principal cached per
    credential, which is what ``GET /user/scopes`` projects — is keyed by the
    raw token and can only be dropped where the request is
    (``CrudRouter._invalidate_creator_principal`` and the deploy-course
    endpoint).

    Call this *after* the membership is committed, or a concurrent read can
    refill the caches from the pre-commit state. Best-effort: a stale cache
    must never fail a write that already landed.
    """
    try:
        from computor_backend.permissions.cache import (
            invalidate_user_course_memberships_sync,
        )
        from computor_backend.redis_cache import get_cache

        invalidate_user_course_memberships_sync(user_id)
        get_cache().invalidate_user_views(user_id=user_id)
    except Exception:
        logger.warning(
            "Cache invalidation after owner enrolment failed for user %s",
            user_id,
            exc_info=True,
        )
