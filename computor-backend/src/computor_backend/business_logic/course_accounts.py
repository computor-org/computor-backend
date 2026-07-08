"""Business logic for linking and provisioning course-member provider accounts.

Thin orchestration layer over the GitLab account-sync engine
(``services.gitlab_account_sync``): resolves the caller's course membership and
provider config, links / verifies their provider account in the DB, then
delegates GitLab membership provisioning to the sync engine.
"""
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from computor_backend.exceptions import (
    BadRequestException,
    NotFoundException,
    UnauthorizedException,
)
from computor_backend.model.auth import Account
from computor_backend.model.course import Course, CourseMember
from computor_backend.permissions.core import check_course_permissions
from computor_backend.permissions.principal import Principal
from computor_backend.services.gitlab_account_sync import (
    _fetch_gitlab_user_profile,
    _sync_gitlab_memberships,
)
from computor_types.accounts import AccountCreate
from computor_types.course_member_accounts import CourseMemberReadinessStatus
from computor_types.courses import CourseProperties
from computor_types.organizations import OrganizationProperties

logger = logging.getLogger(__name__)


def _load_member_with_provider_for_user(
    course_id: UUID | str,
    permissions: Principal,
    db: Session,
):
    """Load course member with provider information."""
    user_id = permissions.get_user_id()
    if not user_id:
        raise NotFoundException()

    course_member = (
        check_course_permissions(permissions, CourseMember, "_student", db)
        .options(
            joinedload(CourseMember.course).joinedload(Course.organization),
            joinedload(CourseMember.user),
        )
        .filter(
            CourseMember.course_id == course_id,
            CourseMember.user_id == user_id,
        )
        .first()
    )

    if not course_member:
        raise NotFoundException()

    course = course_member.course
    if not course:
        raise NotFoundException(detail="Course not found for course member")

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

    provider_url: Optional[str] = None
    if org_props.gitlab and org_props.gitlab.url:
        provider_url = org_props.gitlab.url.strip()
    elif course_props.gitlab and course_props.gitlab.url:
        provider_url = course_props.gitlab.url.strip()

    provider_type = "gitlab" if provider_url else None

    return course_member, provider_url, provider_type, org_props, course_props


def _get_existing_account(db: Session, user_id: UUID | str, provider_url: Optional[str]):
    """Get existing account for user and provider."""
    if not provider_url:
        return None

    return (
        db.query(Account)
        .filter(
            Account.user_id == user_id,
            Account.provider == provider_url,
            Account.type == "gitlab",
        )
        .first()
    )


def _build_validation_status(
    course_member: CourseMember,
    provider_url: Optional[str],
    provider_type: Optional[str],
    existing_account: Optional[Account],
    provider_access_token: Optional[str] = None,
) -> CourseMemberReadinessStatus:
    """Build validation status response."""
    requires_account = bool(provider_url)
    has_account = existing_account is not None

    return CourseMemberReadinessStatus(
        course_member_id=str(course_member.id),
        course_id=str(course_member.course_id),
        organization_id=str(course_member.course.organization_id),
        course_role_id=course_member.course_role_id,
        provider=provider_url,
        provider_type=provider_type,
        requires_account=requires_account,
        has_account=has_account,
        is_ready=(not requires_account) or has_account,
        provider_account_id=existing_account.provider_account_id if existing_account else None,
        provider_access_token=provider_access_token,
    )


def validate_user_course(
    course_id: UUID | str,
    provider_access_token: Optional[str],
    permissions: Principal,
    db: Session,
) -> CourseMemberReadinessStatus:
    """Validate user's course membership and provider account."""
    (
        course_member,
        provider_url,
        provider_type,
        org_props,
        course_props,
    ) = _load_member_with_provider_for_user(course_id, permissions, db)
    existing_account = _get_existing_account(db, course_member.user_id, provider_url)

    if provider_type == "gitlab" and provider_url:
        if not provider_access_token:
            raise UnauthorizedException(
                error_code="GITLAB_005",
                detail="GitLab access token is required to validate and register account"
            )

        # Fetch GitLab user profile from the token
        current_user = _fetch_gitlab_user_profile(provider_url, provider_access_token)
        current_username = (current_user or {}).get("username")
        if not current_username:
            raise BadRequestException(
                error_code="GITLAB_006",
                detail="Unable to determine GitLab user from provided token"
            )

        if existing_account:
            # Validate that token matches existing account
            if current_username.lower() != existing_account.provider_account_id.lower():
                raise BadRequestException(
                    error_code="GITLAB_003",
                    detail="The GitLab access token does not match the linked provider account",
                    context={
                        "actual_username": current_username,
                        "expected_username": existing_account.provider_account_id
                    }
                )
        else:
            # No account exists - create it automatically
            # Check if this GitLab username is already linked to another user
            conflicting_account = (
                db.query(Account)
                .filter(
                    Account.provider == provider_url,
                    Account.type == "gitlab",
                    Account.provider_account_id == current_username,
                    Account.user_id != course_member.user_id,
                )
                .first()
            )

            if conflicting_account:
                raise BadRequestException(
                    error_code="GITLAB_004",
                    detail="This GitLab account is already linked to another user",
                    context={"username": current_username}
                )

            # Create new account
            account_payload = AccountCreate(
                provider=provider_url,
                type="gitlab",
                provider_account_id=current_username,
                user_id=str(course_member.user_id),
            )
            new_account = Account(**account_payload.model_dump())
            db.add(new_account)
            existing_account = new_account
            db.commit()
            db.refresh(existing_account)

            logger.debug(f"✅ Created new GitLab account link: {current_username} → user {course_member.user_id}")
            logger.info("Created GitLab account link for user %s: %s", course_member.user_id, current_username)

        # Sync GitLab memberships
        try:
            _sync_gitlab_memberships(
                provider_url,
                course_member,
                course_props,
                org_props,
                existing_account.provider_account_id,
                db,
                user_access_token=provider_access_token,
            )
        except BadRequestException:
            raise
        except Exception as exc:
            logger.warning("GitLab access provisioning failed during validation: %s", exc)

    return _build_validation_status(
        course_member,
        provider_url,
        provider_type,
        existing_account,
        provider_access_token,
    )


def register_user_course_account(
    course_id: UUID | str,
    provider_account_id: str,
    provider_access_token: Optional[str],
    permissions: Principal,
    db: Session,
) -> CourseMemberReadinessStatus:
    """Register user's provider account for a course."""
    (
        course_member,
        provider_url,
        provider_type,
        org_props,
        course_props,
    ) = _load_member_with_provider_for_user(course_id, permissions, db)

    if not provider_url:
        raise BadRequestException(
            error_code="GITLAB_001",
            detail="Course organization does not define a GitLab provider, no account required"
        )

    provider_account_id = provider_account_id.strip()
    if not provider_account_id:
        raise BadRequestException(
            error_code="GITLAB_008",
            detail="Provider account ID must not be empty"
        )

    provider_access_token = (
        provider_access_token.strip()
        if provider_access_token
        else None
    )

    if provider_type == "gitlab":
        if not provider_access_token:
            raise BadRequestException(
                error_code="GITLAB_005",
                detail="GitLab access token is required to verify account ownership"
            )
        current_user = _fetch_gitlab_user_profile(provider_url, provider_access_token)
        current_username = (current_user or {}).get("username")
        if not current_username:
            raise BadRequestException(
                error_code="GITLAB_006",
                detail="Unable to determine GitLab user from provided token"
            )

        if current_username.lower() != provider_account_id.lower():
            raise BadRequestException(
                error_code="GITLAB_003",
                detail="The GitLab access token does not belong to the specified account",
                context={
                    "actual_username": current_username,
                    "expected_username": provider_account_id
                }
            )

    existing_account = _get_existing_account(db, course_member.user_id, provider_url)

    conflicting_account = (
        db.query(Account)
        .filter(
            Account.provider == provider_url,
            Account.type == "gitlab",
            Account.provider_account_id == provider_account_id,
            Account.user_id != course_member.user_id,
        )
        .first()
    )

    if conflicting_account:
        raise BadRequestException(
            error_code="GITLAB_004",
            detail="Provider account ID is already linked to another user for this provider",
            context={"username": provider_account_id}
        )

    if existing_account:
        if existing_account.provider_account_id == provider_account_id:
            return _build_validation_status(
                course_member,
                provider_url,
                provider_type,
                existing_account,
                provider_access_token,
            )
        existing_account.provider_account_id = provider_account_id
        existing_account.updated_at = func.now()
    else:
        account_payload = AccountCreate(
            provider=provider_url,
            type="gitlab",
            provider_account_id=provider_account_id,
            user_id=str(course_member.user_id),
        )
        new_account = Account(**account_payload.model_dump())
        db.add(new_account)
        existing_account = new_account

    db.commit()
    db.refresh(existing_account)

    try:
        _sync_gitlab_memberships(
            provider_url,
            course_member,
            course_props,
            org_props,
            provider_account_id,
            db,
            user_access_token=provider_access_token,
        )
    except BadRequestException:
        raise
    except Exception as exc:
        logger.warning("GitLab access provisioning failed: %s", exc)

    return _build_validation_status(
        course_member,
        provider_url,
        provider_type,
        existing_account,
        provider_access_token,
    )
