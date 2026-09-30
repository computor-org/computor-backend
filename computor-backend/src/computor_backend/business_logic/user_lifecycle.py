"""User lifecycle predicates and the delete guard.

``login_evidence`` is the single definition of "this user has actually
authenticated": builtin accounts are created only inside the SSO login flow,
API tokens require a session to mint, and the consent gate is only ever passed
by a signed-in person. The connect-users absorption (user_connect.py) and the
invite adoption path (api/invites.py) rely on the same predicate.

``guard_user_delete`` implements the two-step deletion policy from
computor-org/issues#382: a pre-provisioned user that never signed in may be
deleted directly (admin or _user_manager — the same people who create such
rows via import/invite), while a user with a real login history must first be
archived and may then only be deleted by a full admin. Users carrying graded
course work are never deletable — the DB RESTRICT on results is the hard
backstop; this guard turns it into a readable 409 before any cascade runs.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from computor_backend.exceptions import ConflictException, ForbiddenException
from computor_backend.model.auth import Account
from computor_backend.model.consent import UserConsent
from computor_backend.model.course import CourseMember, SubmissionGroupMember
from computor_backend.model.result import Result
from computor_backend.model.role import UserRole
from computor_backend.model.service import ApiToken
from computor_backend.permissions.principal import Principal
from computor_backend.permissions.roles import grants_system_admin

logger = logging.getLogger(__name__)


def login_evidence(user_id: str, db: Session) -> Optional[str]:
    """Why ``user_id`` counts as having authenticated, or ``None`` if they never did."""
    if db.query(Account).filter(
        Account.user_id == user_id, Account.builtin.is_(True)
    ).first():
        return "an SSO/git identity is linked"
    if db.query(ApiToken).filter(ApiToken.user_id == user_id).first():
        return "the user holds API tokens"
    if db.query(UserConsent).filter(UserConsent.user_id == user_id).first():
        return "the user has accepted a consent policy"
    return None


def _has_graded_work(user_id: str, db: Session) -> bool:
    """Any Result under the user's memberships or their submission groups."""
    member_ids = [
        str(row[0])
        for row in db.query(CourseMember.id).filter(CourseMember.user_id == user_id)
    ]
    if not member_ids:
        return False
    if db.query(Result.id).filter(Result.course_member_id.in_(member_ids)).first():
        return True
    group_ids = [
        str(row[0])
        for row in db.query(SubmissionGroupMember.submission_group_id).filter(
            SubmissionGroupMember.course_member_id.in_(member_ids)
        )
    ]
    if group_ids and db.query(Result.id).filter(
        Result.submission_group_id.in_(group_ids)
    ).first():
        return True
    return False


def guard_user_delete(entity, permissions: Principal, db: Session) -> None:
    """Two-step user deletion policy, wired as a ``pre_delete`` CrudRouter guard."""
    user_id = str(entity.id)

    if permissions.user_id and user_id == str(permissions.user_id):
        raise ForbiddenException(detail="You cannot delete your own user account.")

    if entity.is_service:
        raise ConflictException(
            detail="Service accounts cannot be deleted this way. Delete the service instead."
        )

    role_rows = db.query(UserRole.role_id).filter(UserRole.user_id == user_id).all()
    if any(grants_system_admin(row[0]) for row in role_rows):
        raise ForbiddenException(
            detail="Users holding an admin role cannot be deleted. Revoke the admin role first."
        )

    if _has_graded_work(user_id, db):
        raise ConflictException(
            detail="This user has graded course work; deleting them would destroy "
            "grading records. Archive or ban the user instead."
        )

    evidence = login_evidence(user_id, db)
    if evidence is None:
        # Pre-provisioned row (import / invite) that never authenticated —
        # exactly the stuck account from issue #382. Safe to remove.
        return

    if not permissions.is_admin:
        raise ForbiddenException(
            detail="Only administrators can delete a user who has signed in."
        )
    if entity.archived_at is None:
        raise ConflictException(
            detail=f"This user has signed in before ({evidence}). "
            "Archive the user first; an administrator can then delete them."
        )

    logger.warning(
        "User %s (archived, has authenticated) is being deleted by admin %s",
        user_id,
        permissions.user_id,
    )
