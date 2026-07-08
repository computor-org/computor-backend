"""GitLab account-sync engine.

Low-level GitLab HTTP-client logic extracted from
``business_logic/users.py``. This module talks to GitLab (via ``requests``
and ``python-gitlab``) to look up users and provision project/group
memberships for a course member.

Depends only on the model, computor_types and exceptions layers — it must
never import ``business_logic`` (that would create an import cycle, since the
business-logic entry points depend on this engine).
"""
import logging
from urllib.parse import urljoin
from typing import Optional

import requests
from requests import RequestException
from gitlab import Gitlab
from gitlab.exceptions import (
    GitlabCreateError,
    GitlabGetError,
    GitlabHttpError,
)
from sqlalchemy.orm import Session, joinedload

from computor_backend.exceptions import (
    BadRequestException,
    UnauthorizedException,
)
from computor_backend.model.course import CourseMember, SubmissionGroupMember
from computor_types.course_members import CourseMemberProperties
from computor_types.courses import CourseProperties
from computor_types.organizations import OrganizationProperties

logger = logging.getLogger(__name__)


def _fetch_gitlab_user_profile(provider_url: Optional[str], access_token: str) -> dict:
    """Fetch GitLab user profile using access token."""
    if not provider_url:
        raise BadRequestException(
            error_code="GITLAB_001",
            detail="GitLab provider URL is required for verification"
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
            detail="Could not reach GitLab to verify the access token",
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
            detail="Unexpected response from GitLab user API",
            context={"status_code": response.status_code}
        )

    try:
        return response.json()
    except ValueError as exc:
        logger.warning("Failed to decode GitLab user response: %s", exc)
        raise BadRequestException(
            error_code="EXT_001",
            detail="Unexpected response from GitLab user API",
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
        from computor_types.encryption import decrypt_secret
        token = decrypt_secret(token_encrypted)
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


def _get_user_gitlab_client(provider_url: str, user_access_token: str) -> Optional[Gitlab]:
    """Get GitLab client authenticated with user's access token."""
    try:
        client = Gitlab(url=provider_url, private_token=user_access_token)
        return client
    except Exception as exc:
        logger.warning("Unable to initialize user GitLab client: %s", exc)
        return None


def _check_user_has_project_access(
    user_client: Gitlab,
    project_path: str,
    required_access_level: int,
) -> bool:
    """Check if user already has sufficient DIRECT access to a project using their token.

    Note: This checks for direct project membership, not inherited group access.
    This is important because we want to grant explicit Reporter access to student-template
    for students, even if they might have inherited Developer access via a parent group
    (e.g., as a tutor in another course in the same organization).
    """
    try:
        logger.debug(f"🔍 Checking user's DIRECT access to project: {project_path}")

        import requests
        provider_url = user_client.url.rstrip('/')
        headers = {"PRIVATE-TOKEN": user_client.private_token}

        # Get the specific project and check direct membership
        # URL encode the project path
        from urllib.parse import quote
        encoded_path = quote(project_path, safe='')
        project_url = f"{provider_url}/api/v4/projects/{encoded_path}"

        logger.debug(f"  → Fetching project details for: {project_path}")
        response = requests.get(project_url, headers=headers, timeout=10)

        if response.status_code == 404:
            logger.debug(f"  → ✗ Project not found: {project_path}")
            return False
        elif response.status_code != 200:
            logger.debug(f"  → ✗ Failed to get project: HTTP {response.status_code}")
            return False

        project_data = response.json()

        # Check if user has direct membership with sufficient access level
        # The 'permissions' field shows the user's effective permissions
        permissions = project_data.get('permissions', {})
        project_access = permissions.get('project_access')

        if project_access and project_access.get('access_level', 0) >= required_access_level:
            logger.debug(f"  → ✓ User has DIRECT access level {project_access.get('access_level')} (>= {required_access_level}) to project: {project_path}")
            return True

        # Check group_access as fallback (inherited from parent group)
        group_access = permissions.get('group_access')
        if group_access and group_access.get('access_level', 0) >= required_access_level:
            logger.debug(f"  → ℹ️ User has INHERITED group access level {group_access.get('access_level')} (>= {required_access_level})")
            logger.debug(f"  → ⚠️  But we need DIRECT project membership - will grant it explicitly")
            return False  # Return False to force direct membership grant

        logger.debug(f"  → ✗ User does not have direct access level {required_access_level} to project: {project_path}")
        return False

    except (GitlabGetError, GitlabHttpError) as exc:
        # User cannot access project or it doesn't exist
        logger.debug(f"  → ✗ Failed to check project access: {exc}")
        return False
    except Exception as exc:
        logger.debug(f"  → ✗ Unexpected error checking project access: {exc}")
        return False


def _check_user_has_group_access(
    user_client: Gitlab,
    group_full_path: str,
    required_access_level: int,
) -> bool:
    """Check if user already has sufficient DIRECT access to a group using their token.

    Note: This checks for direct group membership, not inherited access from parent groups.
    This ensures we grant explicit membership at the correct level for each role.
    """
    try:
        logger.debug(f"🔍 Checking user's DIRECT access to group: {group_full_path}")

        import requests
        provider_url = user_client.url.rstrip('/')
        headers = {"PRIVATE-TOKEN": user_client.private_token}

        # Get the specific group and check direct membership
        # URL encode the group path
        from urllib.parse import quote
        encoded_path = quote(group_full_path, safe='')
        group_url = f"{provider_url}/api/v4/groups/{encoded_path}"

        logger.debug(f"  → Fetching group details for: {group_full_path}")
        response = requests.get(group_url, headers=headers, timeout=10)

        if response.status_code == 404:
            logger.debug(f"  → ✗ Group not found: {group_full_path}")
            return False
        elif response.status_code != 200:
            logger.debug(f"  → ✗ Failed to get group: HTTP {response.status_code}")
            return False

        group_data = response.json()

        # Get the user's membership in this specific group
        # The 'members' endpoint shows direct members only
        members_url = f"{group_url}/members/all"
        members_response = requests.get(members_url, headers=headers, timeout=10)

        if members_response.status_code != 200:
            logger.debug(f"  → ✗ Failed to get group members: HTTP {members_response.status_code}")
            return False

        # Get current user info to find their user ID
        user_url = f"{provider_url}/api/v4/user"
        user_response = requests.get(user_url, headers=headers, timeout=10)

        if user_response.status_code != 200:
            logger.debug(f"  → ✗ Failed to get current user: HTTP {user_response.status_code}")
            return False

        current_user = user_response.json()
        current_user_id = current_user.get('id')

        # Check if user is a direct member with sufficient access
        all_members = members_response.json()
        for member in all_members:
            if member.get('id') == current_user_id:
                access_level = member.get('access_level', 0)
                if access_level >= required_access_level:
                    logger.debug(f"  → ✓ User has DIRECT access level {access_level} (>= {required_access_level}) to group: {group_full_path}")
                    return True
                else:
                    logger.debug(f"  → ⚠️  User has DIRECT access level {access_level} but needs {required_access_level}")
                    return False

        logger.debug(f"  → ✗ User does not have direct membership in group: {group_full_path}")
        return False

    except (GitlabGetError, GitlabHttpError) as exc:
        # User cannot access group or it doesn't exist
        logger.debug(f"  → ✗ Failed to check group access: {exc}")
        return False
    except Exception as exc:
        logger.debug(f"  → ✗ Unexpected error checking group access: {exc}")
        return False


def _ensure_project_access(
    client: Gitlab,
    project_path: Optional[str],
    gitlab_user_id: int,
    access_level: int,
    context: str,
    user_client: Optional[Gitlab] = None,
):
    """Ensure user has access to a GitLab project."""
    if not project_path:
        return

    # First check if user already has access using their token
    if user_client:
        if _check_user_has_project_access(user_client, project_path, access_level):
            logger.info(
                "✓ SKIPPED GitLab API call - User already has sufficient access to project %s (%s)",
                project_path,
                context,
            )
            logger.debug(f"✓ SKIPPED GitLab API call - User already has access to project: {project_path} ({context})")
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
        logger.debug(f"✅ GRANTED GitLab project access: {project_path} (level={access_level}, {context})")
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
    user_client: Optional[Gitlab] = None,
):
    """Ensure user has access to a GitLab group."""
    if not group_full_path:
        return

    # First check if user already has access using their token
    if user_client:
        if _check_user_has_group_access(user_client, group_full_path, access_level):
            logger.info(
                "✓ SKIPPED GitLab API call - User already has sufficient access to group %s (%s)",
                group_full_path,
                context,
            )
            logger.debug(f"✓ SKIPPED GitLab API call - User already has access to group: {group_full_path} ({context})")
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
        logger.debug(f"✅ GRANTED GitLab group access: {group.full_path} (level={access_level}, {context})")
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
    user_access_token: Optional[str] = None,
):
    """Sync GitLab memberships for course member.

    Args:
        provider_url: GitLab instance URL
        course_member: The course member to sync permissions for
        course_props: Course properties
        org_props: Organization properties
        gitlab_username: GitLab username of the user
        db: Database session
        user_access_token: User's GitLab access token (optional, for checking existing access)
    """
    client = _get_gitlab_client(provider_url, org_props, course_props)
    if not client:
        return

    # Initialize user client if token provided (to check existing access and save API calls)
    user_client = None
    if user_access_token and provider_url:
        user_client = _get_user_gitlab_client(provider_url, user_access_token)
        if user_client:
            logger.info("Using user's token to check existing GitLab access before granting permissions")
            logger.debug(f"🔍 Using user's GitLab token to check existing access (saves system token API calls)")

    gitlab_user_id = _fetch_gitlab_user_id(client, gitlab_username)
    if gitlab_user_id is None:
        raise BadRequestException(
            detail=f"GitLab user '{gitlab_username}' could not be found for access provisioning"
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

        # Collect unique repository paths from all submission groups. This grants
        # GitLab project access, so only GitLab-hosted repos are relevant: read the
        # provider-agnostic 'git' block when its provider is gitlab, else fall back
        # to the legacy GitLab-shaped 'gitlab' block.
        unique_repositories = set()
        for membership in submission_group_memberships:
            submission_group = membership.group
            if submission_group.properties and isinstance(submission_group.properties, dict):
                full_path = None
                git_props = submission_group.properties.get('git')
                if (
                    git_props and isinstance(git_props, dict)
                    and git_props.get('provider') == 'gitlab'
                ):
                    full_path = git_props.get('repo_ref')
                if not full_path:
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
                user_client=user_client,
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
            user_client=user_client,
        )

    elif role == "_tutor":
        if course_props.gitlab and course_props.gitlab.full_path:
            _ensure_group_access(
                client,
                course_props.gitlab.full_path,
                gitlab_user_id,
                30,  # Developer
                "tutor course group membership",
                user_client=user_client,
            )

        if member_props.gitlab and member_props.gitlab.full_path:
            _ensure_project_access(
                client,
                member_props.gitlab.full_path,
                gitlab_user_id,
                40,  # Maintainer
                "tutor repository",
                user_client=user_client,
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
                user_client=user_client,
            )
