"""Shared course/submission-group access ladders.

The "group member OR tutor-and-above" check used to be copy-pasted across
the submissions/tests routers with per-site drift. Both helpers deny
principals that carry no user identity (admins and general-claim holders
must be handled by the caller *before* invoking them, or rely on the
built-in ``is_admin`` short-circuit).
"""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from computor_backend.exceptions import ForbiddenException
from computor_backend.model.course import CourseMember, SubmissionGroupMember
from computor_backend.permissions.core import check_course_permissions
from computor_backend.permissions.principal import Principal


def get_course_member_or_403(
    permissions: Principal,
    course_id: UUID | str,
    db: Session,
    *,
    min_course_role: str = "_student",
    detail: str = "You must be a course member to perform this action",
    error_code: Optional[str] = None,
) -> CourseMember:
    """Return the caller's course membership with at least ``min_course_role``.

    Raises ForbiddenException when the caller is not a member of the course
    at the required role floor. Note that even admins need an actual
    membership row when the returned member is recorded on created rows
    (reviewer, grader, test runner).
    """
    user_id = permissions.get_user_id()
    member = (
        check_course_permissions(permissions, CourseMember, min_course_role, db)
        .filter(
            CourseMember.course_id == course_id,
            CourseMember.user_id == user_id,
        )
        .first()
    )
    if not member:
        kwargs = {"error_code": error_code} if error_code else {}
        raise ForbiddenException(detail=detail, **kwargs)
    return member


def require_submission_group_access(
    permissions: Principal,
    submission_group_id: UUID | str,
    course_id: UUID | str,
    db: Session,
    *,
    min_course_role: str = "_tutor",
    detail: str = "You don't have permission to access this submission group",
    error_code: Optional[str] = None,
) -> None:
    """Allow submission-group members, or course members at ``min_course_role``.

    The standard ladder: admin -> group member -> course role floor -> 403.
    Callers holding a sufficient general claim (e.g. ``submission_artifact:
    list``) should skip this call entirely, mirroring the previous inline
    checks.
    """
    if permissions.is_admin:
        return

    user_id = permissions.get_user_id()
    if not user_id:
        # Principals without a user identity (and without a general claim,
        # which callers check beforehand) must not fall through to access.
        kwargs = {"error_code": error_code} if error_code else {}
        raise ForbiddenException(detail=detail, **kwargs)

    is_group_member = (
        db.query(SubmissionGroupMember)
        .join(CourseMember)
        .filter(
            SubmissionGroupMember.submission_group_id == submission_group_id,
            CourseMember.user_id == user_id,
        )
        .first()
    )
    if is_group_member:
        return

    has_elevated_perms = (
        check_course_permissions(permissions, CourseMember, min_course_role, db)
        .filter(
            CourseMember.course_id == course_id,
            CourseMember.user_id == user_id,
        )
        .first()
    )
    if not has_elevated_perms:
        kwargs = {"error_code": error_code} if error_code else {}
        raise ForbiddenException(detail=detail, **kwargs)
