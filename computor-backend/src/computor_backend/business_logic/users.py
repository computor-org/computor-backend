"""Business logic for user management and authentication."""
import logging
from urllib.parse import urljoin
from typing import Optional, List, Dict
from uuid import UUID

import requests
from requests import RequestException
from gitlab import Gitlab
from gitlab.exceptions import (
    GitlabCreateError,
    GitlabGetError,
    GitlabHttpError,
)
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from computor_backend.api.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
)
from computor_backend.model.auth import Account, User
from computor_backend.model.course import Course, CourseMember, SubmissionGroup, SubmissionGroupMember
from computor_backend.permissions.core import check_course_permissions
from computor_backend.permissions.principal import Principal
from computor_types.accounts import AccountCreate
from computor_types.course_member_accounts import CourseMemberReadinessStatus
from computor_types.course_members import CourseMemberProperties
from computor_types.courses import CourseProperties
from computor_types.organizations import OrganizationProperties
from computor_types.tokens import decrypt_api_key, encrypt_api_key

logger = logging.getLogger(__name__)

COURSE_ROLE_VIEW_MAP: Dict[str, List[str]] = {
    "_student": ["student"],
    "_tutor": ["student", "tutor"],
}
ELEVATED_COURSE_ROLES = {"_lecturer", "_maintainer", "_owner"}


def get_current_user(user_id: str, db: Session) -> User:
    """Get the current authenticated user."""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundException()
        return user
    except Exception as e:
        logger.error(f"Error fetching user: {e}")
        raise NotFoundException()


def set_user_password(
    target_username: Optional[str],
    new_password: str,
    old_password: Optional[str],
    permissions: Principal,
    db: Session,
) -> None:
    """Set or update user password."""

    if target_username is not None and permissions.is_admin is False:
        raise ForbiddenException()

    if len(new_password) < 6:
        raise BadRequestException()

    if target_username is not None:
        user = db.query(User).filter(User.username == target_username).first()

    elif target_username is None and old_password is not None:
        if new_password == old_password:
            raise BadRequestException()

        user = db.query(User).filter(User.id == permissions.get_user_id_or_throw()).first()

        if decrypt_api_key(user.password) != old_password:
            raise BadRequestException()

    else:
        raise ForbiddenException()

    user.password = encrypt_api_key(new_password)
    db.commit()
    db.refresh(user)


def get_course_views_for_user(user_id: str, db: Session) -> List[str]:
    """Get available views based on roles across all courses for the user."""

    # Query all course memberships for the current user
    course_members = (
        db.query(CourseMember)
        .filter(CourseMember.user_id == user_id)
        .all()
    )

    if not course_members:
        return []

    # Collect all unique views from all course roles
    views = set()
    for course_member in course_members:
        if not course_member.course_role_id:
            continue

        role = course_member.course_role_id.lower()

        if role in COURSE_ROLE_VIEW_MAP:
            views.update(COURSE_ROLE_VIEW_MAP[role])
        elif role in ELEVATED_COURSE_ROLES:
            views.update(["student", "tutor", "lecturer"])

    return sorted(list(views))


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


def _fetch_gitlab_user_profile(provider_url: Optional[str], access_token: str) -> dict:
    """Fetch GitLab user profile using access token."""
    if not provider_url:
        raise BadRequestException(
            error_code="GITLAB_001",
            detail="GitLab provider URL is required for verification."
        )

    base_url = provider_url.rstrip("/")
    api_url = urljoin(f"{base_url}/", "api/v4/user")
    headers = {"PRIVATE-TOKEN": access_token}

    try:
        response = requests.get(api_url, headers=headers, timeout=10)
    except RequestException as exc:
        logger.warning("GitLab user lookup failed: %s", exc)
        raise BadRequestException(
            error_code="GITLAB_007",
            detail="Could not reach GitLab to verify the access token.",
            context={"provider_url": provider_url, "error": str(exc)}
        ) from exc

    if response.status_code != 200:
        logger.warning(
            "GitLab user lookup returned %s: %s",
            response.status_code,
            response.text,
        )
        if response.status_code in {401, 403}:
            raise UnauthorizedException(
                error_code="GITLAB_006",
                detail="GitLab rejected the access token. Please ensure it is valid and has API scope.",
                context={"status_code": response.status_code}
            )
        raise BadRequestException(
            error_code="EXT_001",
            detail="Unexpected response from GitLab user API.",
            context={"status_code": response.status_code}
        )

    try:
        return response.json()
    except ValueError as exc:
        logger.warning("Failed to decode GitLab user response: %s", exc)
        raise BadRequestException(
            error_code="EXT_001",
            detail="Unexpected response from GitLab user API.",
            context={"error": str(exc)}
        ) from exc


def _get_gitlab_client(
    provider_url: Optional[str],
    org_props: OrganizationProperties,
    course_props: CourseProperties,
):
    """Get authenticated GitLab client."""
    gitlab_config = None
    if org_props and org_props.gitlab and org_props.gitlab.token:
        gitlab_config = org_props.gitlab
    elif course_props and course_props.gitlab and course_props.gitlab.token:
        gitlab_config = course_props.gitlab

    if not gitlab_config:
        logger.info("GitLab configuration not found; skipping GitLab access provisioning")
        return None

    token_encrypted = gitlab_config.token
    if not token_encrypted:
        logger.info("GitLab token missing in configuration; skipping GitLab access provisioning")
        return None

    gitlab_url = gitlab_config.url or provider_url
    if not gitlab_url:
        logger.info("GitLab URL missing; skipping GitLab access provisioning")
        return None

    try:
        token = decrypt_api_key(token_encrypted)
    except Exception as exc:
        logger.warning("Failed to decrypt GitLab token: %s", exc)
        return None

    try:
        client = Gitlab(url=gitlab_url, private_token=token)
        return client
    except Exception as exc:
        logger.warning("Unable to initialize GitLab client: %s", exc)
        return None


def _fetch_gitlab_user_id(client: Gitlab, username: str) -> Optional[int]:
    """Fetch GitLab user ID by username."""
    try:
        users = client.users.list(username=username)
    except GitlabHttpError as exc:
        logger.warning("GitLab user lookup failed for %s: %s", username, exc)
        return None

    if not users:
        logger.warning("GitLab user %s not found", username)
        return None

    return users[0].id


def _ensure_project_access(
    client: Gitlab,
    project_path: Optional[str],
    gitlab_user_id: int,
    access_level: int,
    context: str,
):
    """Ensure user has access to a GitLab project."""
    if not project_path:
        return

    try:
        project = client.projects.get(project_path)
    except GitlabGetError as exc:
        logger.warning("GitLab project %s not found for %s: %s", project_path, context, exc)
        return

    try:
        project.members.create({"user_id": gitlab_user_id, "access_level": access_level})
        logger.info(
            "Granted GitLab project access: project=%s user_id=%s level=%s (%s)",
            project_path,
            gitlab_user_id,
            access_level,
            context,
        )
    except GitlabCreateError as exc:
        if getattr(exc, "response_code", None) != 409:
            logger.warning(
                "Failed to add member to project %s for %s: %s",
                project_path,
                context,
                exc,
            )
            return
        # Already a member; ensure access level is sufficient
        try:
            member = project.members.get(gitlab_user_id)
            if member.access_level != access_level:
                member.access_level = access_level
                member.save()
                logger.info(
                    "Updated GitLab project access: project=%s user_id=%s level=%s (%s)",
                    project_path,
                    gitlab_user_id,
                    access_level,
                    context,
                )
        except (GitlabGetError, GitlabHttpError) as member_exc:
            logger.warning(
                "Unable to adjust membership for project %s (%s): %s",
                project_path,
                context,
                member_exc,
            )


def _ensure_group_access(
    client: Gitlab,
    group_full_path: Optional[str],
    gitlab_user_id: int,
    access_level: int,
    context: str,
):
    """Ensure user has access to a GitLab group."""
    if not group_full_path:
        return

    try:
        # Use groups.list() with search instead of groups.get() since we have full_path not ID
        groups = list(filter(
            lambda g: g.full_path == group_full_path,
            client.groups.list(search=group_full_path)
        ))

        if not groups:
            logger.warning("GitLab group %s not found for %s", group_full_path, context)
            return

        group = groups[0]
    except GitlabHttpError as exc:
        logger.warning("GitLab group lookup failed for %s (%s): %s", group_full_path, context, exc)
        return

    try:
        group.members.create({"user_id": gitlab_user_id, "access_level": access_level})
        logger.info(
            "Granted GitLab group access: group=%s user_id=%s level=%s (%s)",
            group.full_path,
            gitlab_user_id,
            access_level,
            context,
        )
    except GitlabCreateError as exc:
        if getattr(exc, "response_code", None) != 409:
            logger.warning(
                "Failed to add member to group %s for %s: %s",
                group_full_path,
                context,
                exc,
            )
            return
        try:
            member = group.members.get(gitlab_user_id)
            if member.access_level != access_level:
                member.access_level = access_level
                member.save()
                logger.info(
                    "Updated GitLab group access: group=%s user_id=%s level=%s (%s)",
                    group.full_path,
                    gitlab_user_id,
                    access_level,
                    context,
                )
        except (GitlabGetError, GitlabHttpError) as member_exc:
            logger.warning(
                "Unable to adjust membership for group %s (%s): %s",
                group_full_path,
                context,
                member_exc,
            )


def _sync_gitlab_memberships(
    provider_url: Optional[str],
    course_member: CourseMember,
    course_props: CourseProperties,
    org_props: OrganizationProperties,
    gitlab_username: str,
    db: Session,
):
    """Sync GitLab memberships for course member."""
    client = _get_gitlab_client(provider_url, org_props, course_props)
    if not client:
        return

    gitlab_user_id = _fetch_gitlab_user_id(client, gitlab_username)
    if gitlab_user_id is None:
        raise BadRequestException(
            detail=f"GitLab user '{gitlab_username}' could not be found for access provisioning."
        )

    raw_member_props = course_member.properties or {}
    if isinstance(raw_member_props, CourseMemberProperties):
        member_props = raw_member_props
    else:
        member_props = CourseMemberProperties(**raw_member_props)

    role = (course_member.course_role_id or "").lower()

    if role == "_student":
        # Query all course submission groups that this course member belongs to
        submission_group_memberships = db.query(SubmissionGroupMember)\
            .options(joinedload(SubmissionGroupMember.group))\
            .filter(SubmissionGroupMember.course_member_id == course_member.id)\
            .all()

        # Collect unique repository paths from all submission groups
        unique_repositories = set()
        for membership in submission_group_memberships:
            submission_group = membership.group
            if submission_group.properties and isinstance(submission_group.properties, dict):
                gitlab_props = submission_group.properties.get('gitlab')
                if gitlab_props and isinstance(gitlab_props, dict):
                    full_path = gitlab_props.get('full_path')
                    if full_path:
                        unique_repositories.add(full_path)

        # Grant access to all unique repositories
        for repository_path in unique_repositories:
            _ensure_project_access(
                client,
                repository_path,
                gitlab_user_id,
                40,  # Maintainer
                "student submission repository",
            )

        # Also grant access to the student template repository
        template_path = None
        if course_props.gitlab and course_props.gitlab.full_path:
            template_path = f"{course_props.gitlab.full_path}/student-template"

        _ensure_project_access(
            client,
            template_path,
            gitlab_user_id,
            20,  # Reporter
            "student template",
        )

    elif role == "_tutor":
        if course_props.gitlab and course_props.gitlab.full_path:
            _ensure_group_access(
                client,
                course_props.gitlab.full_path,
                gitlab_user_id,
                30,  # Developer
                "tutor course group membership",
            )

        if member_props.gitlab and member_props.gitlab.full_path:
            _ensure_project_access(
                client,
                member_props.gitlab.full_path,
                gitlab_user_id,
                40,  # Maintainer
                "tutor repository",
            )

    elif role in {"_lecturer", "_maintainer", "_owner"}:
        if course_props.gitlab and course_props.gitlab.full_path:
            access_mapping = {
                "_lecturer": 40,  # Maintainer
                "_maintainer": 40,
                "_owner": 50,  # Owner
            }
            access_level = access_mapping.get(role, 40)
            _ensure_group_access(
                client,
                course_props.gitlab.full_path,
                gitlab_user_id,
                access_level,
                "course group membership",
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
        if existing_account:
            if not provider_access_token:
                raise UnauthorizedException(
                    error_code="GITLAB_005",
                    detail="GitLab access token is required to validate account ownership."
                )

            current_user = _fetch_gitlab_user_profile(provider_url, provider_access_token)
            current_username = (current_user or {}).get("username")
            if not current_username:
                raise BadRequestException(
                    error_code="GITLAB_006",
                    detail="Unable to determine GitLab user from provided token."
                )

            if current_username.lower() != existing_account.provider_account_id.lower():
                raise BadRequestException(
                    error_code="GITLAB_003",
                    detail="The GitLab access token does not match the linked provider account.",
                    context={
                        "actual_username": current_username,
                        "expected_username": existing_account.provider_account_id
                    }
                )
        else:
            # No linked account yet; report readiness without forcing token checks.
            provider_access_token = None

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
            detail="Course organization does not define a GitLab provider, no account required."
        )

    provider_account_id = provider_account_id.strip()
    if not provider_account_id:
        raise BadRequestException(
            error_code="GITLAB_008",
            detail="Provider account ID must not be empty."
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
                detail="GitLab access token is required to verify account ownership."
            )
        current_user = _fetch_gitlab_user_profile(provider_url, provider_access_token)
        current_username = (current_user or {}).get("username")
        if not current_username:
            raise BadRequestException(
                error_code="GITLAB_006",
                detail="Unable to determine GitLab user from provided token."
            )

        if current_username.lower() != provider_account_id.lower():
            raise BadRequestException(
                error_code="GITLAB_003",
                detail="The GitLab access token does not belong to the specified account.",
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
            detail="Provider account ID is already linked to another user for this provider.",
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
