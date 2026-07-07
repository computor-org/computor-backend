"""Course-member → GitLab-member resolution and granting.

Maps computor course members onto GitLab users via the ``Account`` table
(students register their GitLab identity there) and grants project access
through the idempotent primitive in ``git_provider.gitlab``.
"""
import logging
from typing import Optional

from gitlab import Gitlab
from sqlalchemy.orm import Session

from ..model.course import CourseMember
from .gitlab import add_member_idempotent

logger = logging.getLogger(__name__)


def resolve_gitlab_user_id(
    gl: Gitlab,
    db: Session,
    user_id,
    provider_url: Optional[str],
) -> Optional[int]:
    """Resolve a computor user to a numeric GitLab user id, or None.

    Returns None (and logs) when the user has not registered a GitLab
    account for this provider or the username no longer exists on the
    instance.
    """
    from ..model.auth import Account

    account = db.query(Account).filter(
        Account.user_id == user_id,
        Account.provider == provider_url,
        Account.type == "gitlab"
    ).first()

    if not account:
        return None

    gitlab_username = account.provider_account_id
    try:
        users = gl.users.list(username=gitlab_username)
    except Exception as e:
        logger.warning(
            f"Failed to fetch GitLab user ID for username '{gitlab_username}': {e}"
        )
        return None

    if not users:
        logger.warning(
            f"GitLab user '{gitlab_username}' not found on GitLab instance"
        )
        return None

    return users[0].id


def add_course_members_to_project(
    gl: Gitlab,
    project,
    member_ids: list,
    db: Session,
    *,
    access_level: int = 40,
    provider_url: Optional[str] = None,
) -> None:
    """Add course members to a GitLab project (idempotent, never downgrades).

    Gracefully skips members who haven't registered their GitLab account
    yet — permissions are granted later on registration.
    """
    for member_id in member_ids:
        member = db.query(CourseMember).filter(CourseMember.id == member_id).first()
        if not member or not member.user:
            logger.warning(f"CourseMember {member_id} not found or has no user")
            continue

        gitlab_user_id = resolve_gitlab_user_id(gl, db, member.user_id, provider_url)
        if gitlab_user_id is None:
            logger.info(
                f"User {member.user.email} (course_member {member_id}) has no resolvable "
                f"GitLab account - skipping permission grant for project {project.id}"
            )
            continue

        if add_member_idempotent(project, gitlab_user_id, access_level):
            logger.info(
                f"Ensured GitLab user {gitlab_user_id} on project "
                f"{project.path_with_namespace} with access level >= {access_level}"
            )
