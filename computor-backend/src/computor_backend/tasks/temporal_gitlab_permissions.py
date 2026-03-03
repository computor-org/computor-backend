"""
Temporal activity and workflow for granting GitLab permissions to course members.

This module separates permission granting from repository creation so that
Temporal can retry permission grants independently with proper backoff,
handling GitLab rate limits (429) and the case where students haven't
registered their GitLab account yet.
"""
import logging
from datetime import timedelta
from typing import Dict, Any, Optional

from temporalio import workflow, activity
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError
from sqlalchemy.orm import Session
from gitlab import Gitlab
from gitlab.exceptions import GitlabCreateError, GitlabGetError, GitlabHttpError

from .temporal_base import BaseWorkflow, WorkflowResult
from .registry import register_task
from ..database import get_db
from ..model.course import Course, CourseMember
from ..model.organization import Organization
from ..model.auth import Account
from ..gitlab_utils import gitlab_unprotect_branches
from .temporal_student_repository import get_gitlab_client, get_course_gitlab_config
from computor_types.tokens import decrypt_api_key

logger = logging.getLogger(__name__)


class GitlabPermissionError(Exception):
    """Raised when a GitLab permission grant fails due to a transient error
    (e.g., 429 rate limit, 500 server error). Temporal will retry."""
    pass


def _grant_project_access(
    gitlab: Gitlab,
    project_path: str,
    gitlab_user_id: int,
    access_level: int,
    context: str,
) -> None:
    """Grant a user access to a GitLab project. Raises on failure.

    Args:
        gitlab: GitLab client (with admin/org token)
        project_path: Full path of the project (e.g., "org/course/students/user")
        gitlab_user_id: Numeric GitLab user ID
        access_level: GitLab access level (20=Reporter, 40=Maintainer)
        context: Human-readable description for logging

    Raises:
        ApplicationError(non_retryable=True): If project not found (permanent failure)
        GitlabCreateError: On API errors like 429 rate limit (retryable by Temporal)
    """
    try:
        project = gitlab.projects.get(project_path)
    except GitlabGetError as exc:
        raise ApplicationError(
            f"GitLab project '{project_path}' not found ({context}): {exc}",
            non_retryable=True,
        )

    try:
        project.members.create({"user_id": gitlab_user_id, "access_level": access_level})
        logger.info(
            "Granted GitLab access: project=%s user_id=%s level=%s (%s)",
            project_path, gitlab_user_id, access_level, context,
        )
    except GitlabCreateError as exc:
        if getattr(exc, "response_code", None) == 409:
            # Already a member — ensure access level is correct
            try:
                member = project.members.get(gitlab_user_id)
                if member.access_level != access_level:
                    member.access_level = access_level
                    member.save()
                    logger.info(
                        "Updated GitLab access: project=%s user_id=%s level=%s (%s)",
                        project_path, gitlab_user_id, access_level, context,
                    )
                else:
                    logger.info(
                        "User already has correct access: project=%s user_id=%s level=%s (%s)",
                        project_path, gitlab_user_id, access_level, context,
                    )
            except (GitlabGetError, GitlabHttpError) as member_exc:
                logger.warning(
                    "Could not verify/update membership for project %s (%s): %s",
                    project_path, context, member_exc,
                )
                raise member_exc
        else:
            # Any other error (429 rate limit, 500, etc.) — let it propagate for retry
            logger.warning(
                "GitLab API error granting access to project %s (%s): %s (code=%s)",
                project_path, context, exc, getattr(exc, "response_code", "unknown"),
            )
            raise


@activity.defn(name="grant_gitlab_permissions")
async def grant_gitlab_permissions(
    course_member_ids: list[str],
    course_id: str,
    project_full_path: str,
    grant_template_reporter: bool = True,
) -> Dict[str, Any]:
    """
    Grant GitLab permissions for course members.

    Grants Maintainer (40) on the student's/team's repository and optionally
    Reporter (20) on the student-template project.

    RAISES on failure so Temporal can retry with backoff.

    Args:
        course_member_ids: List of CourseMember UUIDs to grant access for
        course_id: Course UUID (to look up organization + student-template path)
        project_full_path: Full path of the student/team repo on GitLab
        grant_template_reporter: Whether to also grant Reporter on student-template

    Returns:
        Dict with results summary

    Raises:
        ApplicationError(non_retryable=True): For permanent failures (project not found, bad config)
        GitlabCreateError/GitlabHttpError: On transient GitLab API errors (retryable by Temporal)
    """
    db = next(get_db())

    try:
        # Load course and organization
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise ApplicationError(f"Course {course_id} not found", non_retryable=True)

        organization = db.query(Organization).filter(Organization.id == course.organization_id).first()
        if not organization:
            raise ApplicationError(
                f"Organization for course {course_id} not found", non_retryable=True
            )

        # Get GitLab client and config
        gitlab = get_gitlab_client(organization)
        gitlab_url = organization.properties.get("gitlab", {}).get("url")

        # Get student-template path for Reporter access
        template_project_path = None
        if grant_template_reporter:
            try:
                gitlab_config = get_course_gitlab_config(course, gitlab)
                template_project_path = gitlab_config.get("template_path")
            except ValueError as exc:
                logger.warning("Could not determine student-template path: %s", exc)
                # Not a fatal error — we still grant Maintainer on the student repo

        members_granted = []
        members_skipped = []

        for course_member_id in course_member_ids:
            course_member = db.query(CourseMember).filter(
                CourseMember.id == course_member_id
            ).first()
            if not course_member:
                raise ApplicationError(
                    f"CourseMember {course_member_id} not found", non_retryable=True
                )

            # Look up GitLab account
            account = db.query(Account).filter(
                Account.user_id == course_member.user_id,
                Account.provider == gitlab_url,
                Account.type == "gitlab",
            ).first()

            if not account:
                user_email = course_member.user.email if course_member.user else "unknown"
                logger.info(
                    "Skipping permission grant for user %s (course_member %s) — "
                    "no GitLab account registered yet",
                    user_email, course_member_id,
                )
                members_skipped.append(course_member_id)
                continue

            gitlab_username = account.provider_account_id

            # Resolve GitLab numeric user ID
            users = gitlab.users.list(username=gitlab_username)
            if not users:
                raise ApplicationError(
                    f"GitLab user '{gitlab_username}' not found on GitLab instance",
                    non_retryable=True,
                )
            gitlab_user_id = users[0].id

            # Grant Maintainer (40) on the student/team repository
            _grant_project_access(
                gitlab, project_full_path, gitlab_user_id, 40,
                f"student repo for {gitlab_username}",
            )

            # Grant Reporter (20) on student-template
            if template_project_path:
                _grant_project_access(
                    gitlab, template_project_path, gitlab_user_id, 20,
                    f"student-template reporter for {gitlab_username}",
                )

            # Mark permissions as granted on this CourseMember
            from sqlalchemy.orm.attributes import flag_modified
            course_member.properties = course_member.properties or {}
            course_member.properties["gitlab_permissions_status"] = "granted"
            flag_modified(course_member, "properties")
            db.add(course_member)

            members_granted.append(course_member_id)
            logger.info(
                "GitLab permissions granted for course_member %s (gitlab user: %s)",
                course_member_id, gitlab_username,
            )

        db.commit()

        return {
            "success": True,
            "members_granted": members_granted,
            "members_skipped": members_skipped,
            "project_full_path": project_full_path,
        }

    except (GitlabPermissionError, GitlabCreateError, GitlabHttpError):
        # Retryable errors — let Temporal handle them
        raise
    except ApplicationError:
        # Non-retryable errors — propagate as-is
        raise
    except Exception as exc:
        logger.error("Unexpected error in grant_gitlab_permissions: %s", exc, exc_info=True)
        raise
    finally:
        db.close()


@register_task
@workflow.defn(name="GrantGitlabPermissionsWorkflow", sandboxed=False)
class GrantGitlabPermissionsWorkflow(BaseWorkflow):
    """
    Standalone workflow for granting GitLab permissions with retry.

    Can be triggered from:
    - StudentRepositoryCreationWorkflow (as second step after repo creation)
    - Sign-up path (validate_user_course / register_user_course_account) on sync failure
    - Manual lecturer sync
    """

    @classmethod
    def get_name(cls) -> str:
        return "GrantGitlabPermissionsWorkflow"

    @workflow.run
    async def run(self, params: Dict[str, Any]) -> WorkflowResult:
        """
        Execute GitLab permission granting with generous retry policy.

        Expected params:
            course_member_ids: List of CourseMember UUIDs
            course_id: Course UUID
            project_full_path: Full GitLab path of the student/team repo
            grant_template_reporter: bool (default True)
        """
        permission_retry_policy = RetryPolicy(
            maximum_attempts=10,
            initial_interval=timedelta(seconds=60),
            maximum_interval=timedelta(seconds=60),
            backoff_coefficient=1.0,
        )

        try:
            result = await workflow.execute_activity(
                grant_gitlab_permissions,
                args=[
                    params["course_member_ids"],
                    params["course_id"],
                    params["project_full_path"],
                    params.get("grant_template_reporter", True),
                ],
                retry_policy=permission_retry_policy,
                start_to_close_timeout=timedelta(minutes=15),
            )

            return WorkflowResult(
                status="success",
                result=result,
                metadata={"members_granted": len(result.get("members_granted", []))},
            )

        except Exception as e:
            logger.error("GrantGitlabPermissionsWorkflow failed: %s", e)
            return WorkflowResult(
                status="failed",
                result=None,
                error=str(e),
                metadata={"error_details": str(e)},
            )
