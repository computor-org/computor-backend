"""Shared course/submission-group access ladders.

The "group member OR tutor-and-above" check used to be copy-pasted across
the submissions/tests routers with per-site drift. Both helpers deny
principals that carry no user identity (admins and general-claim holders
must be handled by the caller *before* invoking them, or rely on the
built-in ``is_admin`` short-circuit).

404-vs-403 on denial (TASK-209)
-------------------------------
Both helpers accept an ``exception`` knob so the call site can express
*why* access is denied (see the convention in
``exceptions.exceptions``):

- ``require_submission_group_access`` gates *visibility* of a submission
  group's artifacts/grades/results — a caller who fails it could not see
  the resource by any other route, so it **defaults to hiding existence**
  (:class:`PermissionDeniedAsNotFound`, a 404), matching the generated
  CrudRouter routes.
- ``get_course_member_or_403`` is used both for pure visibility gates
  (viewing/creating reviews needs course membership) *and* for
  action-denial on an already-visible resource (a group student can see
  their submission but not grade it). Its name and historical behaviour
  are 403, so it **defaults to** :class:`ForbiddenException`; call sites
  that hide existence pass ``exception=PermissionDeniedAsNotFound``.

Neither the ``exception`` knob nor these defaults change *who* is allowed
— only what is raised on the deny branch.
"""
from typing import Optional, Type
from uuid import UUID

from sqlalchemy.orm import Session

from computor_backend.exceptions import ForbiddenException, PermissionDeniedAsNotFound
from computor_backend.exceptions.exceptions import ComputorException
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
    exception: Type[ComputorException] = ForbiddenException,
) -> CourseMember:
    """Return the caller's course membership with at least ``min_course_role``.

    Raises ``exception`` (default :class:`ForbiddenException`, a 403) when the
    caller is not a member of the course at the required role floor. Note that
    even admins need an actual membership row when the returned member is
    recorded on created rows (reviewer, grader, test runner).

    Pass ``exception=PermissionDeniedAsNotFound`` at call sites where a denied
    caller could not otherwise see the resource (existence hiding, 404); keep
    the default 403 for action-denial on a resource the caller can already
    see. See the 404-vs-403 convention in ``exceptions.exceptions``. The name
    is retained for back-compat (it is imported widely); the default surface is
    still a 403.
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
        raise exception(detail=detail, **kwargs)
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
    exception: Type[ComputorException] = PermissionDeniedAsNotFound,
) -> None:
    """Allow submission-group members, or course members at ``min_course_role``.

    The standard ladder: admin -> group member -> course role floor -> deny.
    Callers holding a sufficient general claim (e.g. ``submission_artifact:
    list``) should skip this call entirely, mirroring the previous inline
    checks.

    Denial raises ``exception``, which **defaults to**
    :class:`PermissionDeniedAsNotFound` (a 404): a caller who fails this ladder
    could not otherwise see the submission group's artifacts/grades/results, so
    existence is hidden (matching the generated CrudRouter routes). Pass an
    explicit ``exception`` only if a specific site legitimately exposes the
    resource and should merely deny an action (403). See the 404-vs-403
    convention in ``exceptions.exceptions``.
    """
    if permissions.is_admin:
        return

    user_id = permissions.get_user_id()
    if not user_id:
        # Principals without a user identity (and without a general claim,
        # which callers check beforehand) must not fall through to access.
        kwargs = {"error_code": error_code} if error_code else {}
        raise exception(detail=detail, **kwargs)

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
        raise exception(detail=detail, **kwargs)
