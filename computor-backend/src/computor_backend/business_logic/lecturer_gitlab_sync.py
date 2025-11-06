"""Business logic for lecturer-initiated GitLab permission synchronization."""
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from computor_backend.api.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from computor_backend.model.course import Course, CourseMember
from computor_backend.model.auth import Account
from computor_backend.permissions.core import check_course_permissions
from computor_backend.permissions.principal import Principal
from computor_types.courses import CourseProperties
from computor_types.organizations import OrganizationProperties
from computor_types.lecturer_gitlab_sync import GitLabSyncResult

from .users import (
    _get_gitlab_client,
    _fetch_gitlab_user_id,
    _sync_gitlab_memberships,
)

logger = logging.getLogger(__name__)


def sync_course_member_gitlab_permissions(
    course_member_id: UUID | str,
    permissions: Principal,
    db: Session,
    force: bool = False,
) -> GitLabSyncResult:
    """
    Sync GitLab permissions for a specific course member.

    This endpoint allows lecturers to manually trigger GitLab permission sync
    for a course member. Useful when:
    - New assignments/repositories added
    - Member role changed
    - GitLab configuration updated
    - Initial setup issues

    Args:
        course_member_id: CourseMember UUID
        permissions: Current principal (must be _lecturer or higher)
        db: Database session
        force: Force sync even if recently synced

    Returns:
        GitLabSyncResult with sync details

    Raises:
        ForbiddenException: If user lacks _lecturer permissions
        NotFoundException: If course member not found
        BadRequestException: If GitLab not configured
    """
    # Fetch course member with relationships
    course_member = (
        db.query(CourseMember)
        .options(
            joinedload(CourseMember.course).joinedload(Course.organization),
            joinedload(CourseMember.user),
        )
        .filter(CourseMember.id == course_member_id)
        .first()
    )

    if not course_member:
        raise NotFoundException(detail="Course member not found")

    # Verify lecturer permissions on the course
    course = check_course_permissions(permissions, Course, "_lecturer", db).filter(
        Course.id == course_member.course_id
    ).first()

    if not course:
        raise ForbiddenException(
            detail="You must be a lecturer or higher to sync GitLab permissions"
        )

    # Get organization and course properties
    organization = course.organization
    if not organization:
        raise NotFoundException(detail="Organization not found for course")

    org_props = (
        OrganizationProperties(**organization.properties)
        if organization.properties
        else OrganizationProperties()
    )

    course_props = (
        CourseProperties(**course.properties)
        if course.properties
        else CourseProperties()
    )

    # Determine GitLab provider URL
    provider_url: Optional[str] = None
    if org_props.gitlab and org_props.gitlab.url:
        provider_url = org_props.gitlab.url.strip()
    elif course_props.gitlab and course_props.gitlab.url:
        provider_url = course_props.gitlab.url.strip()

    if not provider_url:
        raise BadRequestException(
            error_code="GITLAB_001",
            detail="GitLab integration not configured for this course"
        )

    # Get GitLab account for user
    account = (
        db.query(Account)
        .filter(
            Account.user_id == course_member.user_id,
            Account.provider == provider_url,
            Account.type == "gitlab",
        )
        .first()
    )

    if not account:
        return GitLabSyncResult(
            course_member_id=str(course_member.id),
            user_id=str(course_member.user_id),
            username=course_member.user.username,
            course_role_id=course_member.course_role_id,
            sync_status="skipped",
            message="User has not linked their GitLab account yet",
            permissions_granted=[],
            permissions_updated=[],
            api_calls_made=0,
        )

    gitlab_username = account.provider_account_id

    # Verify GitLab user exists
    client = _get_gitlab_client(provider_url, org_props, course_props)
    if not client:
        raise BadRequestException(
            detail="Failed to initialize GitLab client. Check organization/course configuration."
        )

    gitlab_user_id = _fetch_gitlab_user_id(client, gitlab_username)
    if gitlab_user_id is None:
        return GitLabSyncResult(
            course_member_id=str(course_member.id),
            user_id=str(course_member.user_id),
            username=course_member.user.username,
            course_role_id=course_member.course_role_id,
            sync_status="failed",
            message=f"GitLab user '{gitlab_username}' not found on GitLab instance",
            permissions_granted=[],
            permissions_updated=[],
            api_calls_made=1,
        )

    # Perform sync
    try:
        start_time = datetime.now(timezone.utc)

        _sync_gitlab_memberships(
            provider_url=provider_url,
            course_member=course_member,
            course_props=course_props,
            org_props=org_props,
            gitlab_username=gitlab_username,
            db=db,
            user_access_token=None,  # Lecturer-initiated, no user token available
        )

        end_time = datetime.now(timezone.utc)

        return GitLabSyncResult(
            course_member_id=str(course_member.id),
            user_id=str(course_member.user_id),
            username=course_member.user.username,
            course_role_id=course_member.course_role_id,
            sync_status="success",
            message="GitLab permissions synchronized successfully",
            permissions_granted=[],  # TODO: Track what was granted
            permissions_updated=[],  # TODO: Track what was updated
            api_calls_made=0,  # TODO: Count API calls
            synced_at=end_time,
        )

    except Exception as exc:
        logger.error(f"Failed to sync GitLab permissions for course member {course_member.id}: {exc}")
        return GitLabSyncResult(
            course_member_id=str(course_member.id),
            user_id=str(course_member.user_id),
            username=course_member.user.username,
            course_role_id=course_member.course_role_id,
            sync_status="failed",
            message=f"Sync failed: {str(exc)}",
            permissions_granted=[],
            permissions_updated=[],
            api_calls_made=0,
        )
