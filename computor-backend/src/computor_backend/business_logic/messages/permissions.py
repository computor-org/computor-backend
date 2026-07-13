"""Per-target write-permission checks for message creation."""
from sqlalchemy.orm import Session

from computor_backend.exceptions import ForbiddenException, NotImplementedException
from computor_backend.permissions.principal import Principal, course_role_hierarchy
from computor_backend.permissions.roles import CourseRole, ScopeRole
from computor_backend.model.course import (
    CourseContent,
    CourseGroup,
    CourseMember,
    SubmissionGroup,
    SubmissionGroupMember,
)


def _principal_has_course_role(
    permissions: Principal,
    course_id,
    min_role: str,
    db: Session,
) -> bool:
    """Whether the principal holds at least ``min_role`` in ``course_id``.

    Hits the database directly (claims may be stale right after a role
    change). Admins always pass. Used by every write check that needs a
    "lecturer-or-above on this course" gate — the role list is derived
    from ``course_role_hierarchy`` so it tracks the hierarchy, not a
    hard-coded literal.
    """
    if permissions.is_admin:
        return True
    allowed = course_role_hierarchy.get_allowed_roles(min_role)
    return bool(db.query(
        db.query(CourseMember.id)
        .filter(
            CourseMember.course_id == course_id,
            CourseMember.user_id == permissions.user_id,
            CourseMember.course_role_id.in_(allowed),
        )
        .exists()
    ).scalar())


def _check_global_write_permission(permissions: Principal) -> None:
    """Global messages (no target set) are admin-only."""
    if not permissions.is_admin:
        raise ForbiddenException(
            detail="Only administrators can create global messages"
        )


def _check_user_message_write_permission(
    permissions: Principal,
    user_id: str,
    db: Session,
) -> None:
    """Direct user-to-user message (one-on-one chat).

    The handler path is wired end-to-end (visibility, audit, broadcast)
    but creation is intentionally disabled until the product side
    settles on rate-limiting / abuse handling. To enable: drop the raise
    below — the rest of the path is already correct.

    Intended rules when enabled:
    - recipient must exist
    - author must not message themselves
    - no role required (this is a direct chat)
    """
    raise NotImplementedException(
        detail="Direct user-to-user messages are not implemented yet"
    )


def _check_organization_write_permission(
    permissions: Principal,
    organization_id: str,
) -> None:
    """Organization messages: scoped role >= _manager (admin bypass).

    ``_developer`` is intentionally excluded — org-level announcements are
    a higher-trust action than ordinary org administration.
    """
    if not permissions.has_organization_role(organization_id, ScopeRole.MANAGER):
        raise ForbiddenException(
            detail="Requires organization _manager or _owner role to post organization messages"
        )


def _check_course_family_write_permission(
    permissions: Principal,
    course_family_id: str,
) -> None:
    """Course-family messages: scoped role >= _manager (admin bypass)."""
    if not permissions.has_course_family_role(course_family_id, ScopeRole.MANAGER):
        raise ForbiddenException(
            detail="Requires course_family _manager or _owner role to post course family messages"
        )


def _check_course_group_write_permission(
    permissions: Principal,
    course_group_id: str,
    db: Session,
) -> None:
    """Course-group messages: course role >= _lecturer in the group's course."""
    course_group = db.query(CourseGroup).filter(CourseGroup.id == course_group_id).first()
    if not course_group:
        raise ForbiddenException(detail="Course group not found")

    if not _principal_has_course_role(
        permissions, course_group.course_id, CourseRole.LECTURER, db
    ):
        raise ForbiddenException()


def _check_submission_group_write_permission(
    permissions: Principal,
    submission_group_id: str,
    db: Session,
) -> None:
    """Check if user can write to a submission group.

    Rules:
    - User must be a submission_group_member OR
    - User must have a course role of _tutor or above in the submission group's course

    Raises:
        ForbiddenException: If user lacks permission
    """
    if permissions.is_admin:
        return

    # Check if user is a submission group member
    is_member = db.query(
        db.query(SubmissionGroupMember.id)
        .join(CourseMember, CourseMember.id == SubmissionGroupMember.course_member_id)
        .filter(
            SubmissionGroupMember.submission_group_id == submission_group_id,
            CourseMember.user_id == permissions.user_id
        )
        .exists()
    ).scalar()

    if is_member:
        return

    # Fall back to course-role check (anyone above _student qualifies).
    submission_group = db.query(SubmissionGroup).filter(
        SubmissionGroup.id == submission_group_id
    ).first()

    if not submission_group:
        raise ForbiddenException(detail="Submission group not found")

    if not _principal_has_course_role(
        permissions, submission_group.course_id, CourseRole.TUTOR, db
    ):
        raise ForbiddenException(detail="You must be a submission group member or have elevated course role to write messages to this submission group")


def _check_course_content_write_permission(
    permissions: Principal,
    course_content_id: str,
    db: Session,
) -> None:
    """Course-content messages: course role >= _lecturer in the content's course."""
    course_content = db.query(CourseContent).filter(
        CourseContent.id == course_content_id
    ).first()

    if not course_content:
        raise ForbiddenException(detail="Course content not found")

    if not _principal_has_course_role(
        permissions, course_content.course_id, CourseRole.LECTURER, db
    ):
        raise ForbiddenException()


def _check_course_write_permission(
    permissions: Principal,
    course_id: str,
    db: Session,
) -> None:
    """Course messages: course role >= _lecturer in the course."""
    if not _principal_has_course_role(
        permissions, course_id, CourseRole.LECTURER, db
    ):
        raise ForbiddenException()
