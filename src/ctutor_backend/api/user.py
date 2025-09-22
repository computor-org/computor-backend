from typing import Annotated, Optional
from uuid import UUID

import logging
from urllib.parse import urljoin

from fastapi import APIRouter, Body, Depends
from gitlab import Gitlab
from gitlab.exceptions import (
    GitlabCreateError,
    GitlabGetError,
    GitlabHttpError,
)
import requests
from requests import RequestException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from ctutor_backend.api.exceptions import BadRequestException, NotFoundException, UnauthorizedException
from ctutor_backend.database import get_db
from ctutor_backend.interface.accounts import AccountCreate
from ctutor_backend.interface.course_member_accounts import (
    CourseMemberProviderAccountUpdate,
    CourseMemberReadinessStatus,
    CourseMemberValidationRequest,
)
from ctutor_backend.interface.course_members import CourseMemberProperties
from ctutor_backend.interface.courses import CourseProperties
from ctutor_backend.interface.organizations import OrganizationProperties
from ctutor_backend.interface.tokens import decrypt_api_key, encrypt_api_key
from ctutor_backend.interface.users import UserGet
from ctutor_backend.model.auth import Account, User
from ctutor_backend.model.course import Course, CourseMember
from ctutor_backend.permissions.auth import get_current_permissions
from ctutor_backend.permissions.core import check_course_permissions
from ctutor_backend.permissions.principal import Principal

logger = logging.getLogger(__name__)

user_router = APIRouter()


def _load_member_with_provider_for_user(
    course_id: UUID | str,
    permissions: Principal,
    db: Session,
):
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


def _get_gitlab_client(
    provider_url: Optional[str],
    org_props: OrganizationProperties,
    course_props: CourseProperties,
):
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
    group_identifier: Optional[str | int],
    gitlab_user_id: int,
    access_level: int,
    context: str,
):
    if not group_identifier:
        return

    try:
        group = client.groups.get(group_identifier)
    except GitlabGetError as exc:
        logger.warning("GitLab group %s not found for %s: %s", group_identifier, context, exc)
        return

    try:
        group.members.create({"user_id": gitlab_user_id, "access_level": access_level})
        logger.info(
            "Granted GitLab group access: group=%s user_id=%s level=%s (%s)",
            getattr(group, "full_path", group_identifier),
            gitlab_user_id,
            access_level,
            context,
        )
    except GitlabCreateError as exc:
        if getattr(exc, "response_code", None) != 409:
            logger.warning(
                "Failed to add member to group %s for %s: %s",
                group_identifier,
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
                    getattr(group, "full_path", group_identifier),
                    gitlab_user_id,
                    access_level,
                    context,
                )
        except (GitlabGetError, GitlabHttpError) as member_exc:
            logger.warning(
                "Unable to adjust membership for group %s (%s): %s",
                group_identifier,
                context,
                member_exc,
            )


def _sync_gitlab_memberships(
    provider_url: Optional[str],
    course_member: CourseMember,
    course_props: CourseProperties,
    org_props: OrganizationProperties,
    gitlab_username: str,
):
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
        if member_props.gitlab and member_props.gitlab.full_path:
            _ensure_project_access(
                client,
                member_props.gitlab.full_path,
                gitlab_user_id,
                40,  # Maintainer
                "student repository",
            )

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
        if course_props.gitlab:
            group_identifier = course_props.gitlab.group_id or course_props.gitlab.full_path
            _ensure_group_access(
                client,
                group_identifier,
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
        if course_props.gitlab:
            group_identifier = course_props.gitlab.group_id or course_props.gitlab.full_path
            access_mapping = {
                "_lecturer": 40,  # Maintainer
                "_maintainer": 40,
                "_owner": 50,  # Owner
            }
            access_level = access_mapping.get(role, 40)
            _ensure_group_access(
                client,
                group_identifier,
                gitlab_user_id,
                access_level,
                "course group membership",
            )


def _fetch_gitlab_user_profile(
    provider_url: Optional[str],
    access_token: str,
) -> dict:
    if not provider_url:
        raise BadRequestException("GitLab provider URL is required for verification.")

    base_url = provider_url.rstrip("/")
    api_url = urljoin(f"{base_url}/", "api/v4/user")
    headers = {"PRIVATE-TOKEN": access_token}

    try:
        response = requests.get(api_url, headers=headers, timeout=10)
    except RequestException as exc:
        logger.warning("GitLab user lookup failed: %s", exc)
        raise BadRequestException(
            "Could not reach GitLab to verify the access token."
        ) from exc

    if response.status_code != 200:
        logger.warning(
            "GitLab user lookup returned %s: %s",
            response.status_code,
            response.text,
        )
        if response.status_code in {401, 403}:
            raise UnauthorizedException(
                "GitLab rejected the access token. Please ensure it is valid and has API scope."
            )
        raise BadRequestException("Unexpected response from GitLab user API.")

    try:
        return response.json()
    except ValueError as exc:  # noqa: B902
        logger.warning("Failed to decode GitLab user response: %s", exc)
        raise BadRequestException("Unexpected response from GitLab user API.") from exc



@user_router.get("", response_model=UserGet)
def get_current_user(
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    db: Session = Depends(get_db)
):
    """Get the current authenticated user"""
    try:
        return db.query(User).filter(User.id == permissions.user_id).first()
    except Exception as e:
        print(e)
        raise NotFoundException()

class UserPassword(BaseModel):
    username: str
    password: str

@user_router.post("/password", status_code=204)
def set_user_password(permissions: Annotated[Principal, Depends(get_current_permissions)], payload: UserPassword, db: Session = Depends(get_db)):

    # TODO: add report, this should not be called from someone else
    if permissions.is_admin == False:
        raise NotFoundException()

    if len(payload.password) < 6:
        raise BadRequestException()

    if payload.username == None or len(payload.username) < 3:
        raise BadRequestException()

    with next(get_db()) as db:
        user = db.query(User).filter(User.username == payload.username).first()

        user.password = encrypt_api_key(payload.password)
        db.commit()
        db.refresh(user)


@user_router.post(
    "/courses/{course_id}/validate",
    response_model=CourseMemberReadinessStatus,
)
async def validate_current_user_course(
    course_id: UUID | str,
    validation: CourseMemberValidationRequest,
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    db: Session = Depends(get_db),
):
    (
        course_member,
        provider_url,
        provider_type,
        org_props,
        course_props,
    ) = _load_member_with_provider_for_user(course_id, permissions, db)
    existing_account = _get_existing_account(db, course_member.user_id, provider_url)

    validation = validation or CourseMemberValidationRequest()
    provider_access_token = validation.provider_access_token

    if provider_type == "gitlab" and provider_url:
        if existing_account:
            if not provider_access_token:
                raise UnauthorizedException(
                    "GitLab access token is required to validate account ownership."
                )

            current_user = _fetch_gitlab_user_profile(provider_url, provider_access_token)
            current_username = (current_user or {}).get("username")
            if not current_username:
                raise BadRequestException("Unable to determine GitLab user from provided token.")

            if current_username.lower() != existing_account.provider_account_id.lower():
                raise BadRequestException(
                    "The GitLab access token does not match the linked provider account."
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


@user_router.post(
    "/courses/{course_id}/register",
    response_model=CourseMemberReadinessStatus,
)
async def register_current_user_course_account(
    course_id: UUID | str,
    payload: CourseMemberProviderAccountUpdate,
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    db: Session = Depends(get_db),
):
    (
        course_member,
        provider_url,
        provider_type,
        org_props,
        course_props,
    ) = _load_member_with_provider_for_user(course_id, permissions, db)

    if not provider_url:
        raise BadRequestException(
            "Course organization does not define a GitLab provider, no account required."
        )

    provider_account_id = payload.provider_account_id.strip()
    if not provider_account_id:
        raise BadRequestException("Provider account ID must not be empty.")

    provider_access_token = (
        payload.provider_access_token.strip()
        if payload.provider_access_token
        else None
    )

    if provider_type == "gitlab":
        if not provider_access_token:
            raise BadRequestException(
                "GitLab access token is required to verify account ownership."
            )
        current_user = _fetch_gitlab_user_profile(provider_url, provider_access_token)
        current_username = (current_user or {}).get("username")
        if not current_username:
            raise BadRequestException("Unable to determine GitLab user from provided token.")

        if current_username.lower() != provider_account_id.lower():
            raise BadRequestException(
                "The GitLab access token does not belong to the specified account."
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
            "Provider account ID is already linked to another user for this provider."
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
