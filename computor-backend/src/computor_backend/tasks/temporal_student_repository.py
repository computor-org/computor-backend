"""
LEGACY Temporal activities for org-level GitLab student/team repositories.

Scope: this module ONLY runs for un-migrated, org-level GitLab courses that still
fork the ``student-template`` project directly. Courses migrated to
``CourseGitBinding`` (course-level, binding-driven provisioning) do NOT use this
module.

Retirement condition: once all courses have been migrated to ``CourseGitBinding``
this module has no remaining callers and can be deleted.

Do NOT extend this module for Forgejo or any other new provider -- new
provisioning must go through the ``git_provider`` binding-driven path instead.

This module handles forking the student-template repository when students join a
course, for both individual and team repositories.
"""
import logging
import asyncio
import json
import re
from datetime import timedelta
from typing import Dict, Any, Optional
from uuid import UUID

from temporalio import workflow, activity
from temporalio.common import RetryPolicy
from sqlalchemy.orm import Session
from gitlab import Gitlab
from gitlab.exceptions import GitlabGetError

from .temporal_base import BaseWorkflow, WorkflowResult
from .registry import register_task
from ..database import get_db_session
from ..model.course import Course, CourseMember, SubmissionGroup, SubmissionGroupMember
from ..gitlab_utils import construct_gitlab_http_url, construct_gitlab_ssh_url, construct_gitlab_web_url
from ..model.organization import Organization
from computor_types.encryption import decrypt_secret
from ..git_provider.gitlab import (
    fork_project_with_polling,
    gitlab_unprotect_branches,
    make_gitlab_client,
)
from ..git_provider.gitlab_members import add_course_members_to_project

logger = logging.getLogger(__name__)




def get_gitlab_client(organization: Organization) -> Gitlab:
    """
    Get a configured GitLab client from organization settings.
    
    Args:
        organization: The organization with GitLab configuration
        
    Returns:
        Configured GitLab client
        
    Raises:
        ValueError: If GitLab configuration is missing or invalid
    """
    org_properties = organization.properties or {}
    gitlab_config = org_properties.get('gitlab', {})
    gitlab_url = gitlab_config.get('url')
    gitlab_token_encrypted = gitlab_config.get('token')
    
    if not gitlab_url or not gitlab_token_encrypted:
        raise ValueError(f"Organization {organization.id} missing GitLab configuration")
    
    gitlab_token = decrypt_secret(gitlab_token_encrypted)

    return make_gitlab_client(gitlab_url, gitlab_token)


def get_course_gitlab_config(course: Course, gitlab: Optional[Gitlab] = None) -> Dict[str, Any]:
    """
    Extract the students-group / course-group GitLab configuration from course
    properties.

    Note: student-template project resolution now lives in
    ``_resolve_template_project`` (single copy) -- this helper only resolves the
    students group namespace (with auto-discovery) and the course group id.

    Args:
        course: The course object
        gitlab: Optional GitLab client for finding a missing students subgroup

    Returns:
        GitLab configuration dictionary

    Raises:
        ValueError: If the students group cannot be resolved
    """
    course_properties = course.properties or {}
    gitlab_props = course_properties.get('gitlab', {})

    # Get students group ID with fallbacks
    students_group_id = gitlab_props.get('students_group', {}).get('group_id')

    # If missing, try to find it in GitLab
    if not students_group_id and gitlab:
        course_group_id = gitlab_props.get('group_id')
        if course_group_id:
            try:
                # Look for students subgroup
                parent_group = gitlab.groups.get(course_group_id)
                for subgroup in parent_group.subgroups.list(all=True):
                    if subgroup.path == 'students':
                        students_group_id = subgroup.id
                        logger.warning(f"Found students group {subgroup.id} not stored in course properties")

                        # Update course properties for future use
                        from sqlalchemy.orm import Session
                        from sqlalchemy.orm.attributes import flag_modified
                        db = Session.object_session(course)
                        if db:
                            if not course.properties:
                                course.properties = {}
                            if "gitlab" not in course.properties:
                                course.properties["gitlab"] = {}
                            course.properties["gitlab"]["students_group"] = {
                                "group_id": students_group_id,
                                "full_path": subgroup.full_path
                            }
                            flag_modified(course, "properties")
                            db.add(course)
                            db.commit()
                            logger.info(f"Updated course {course.id} with students group info")
                        break
            except Exception as e:
                logger.warning(f"Could not search for students group: {e}")

    if not students_group_id:
        raise ValueError(f"Course {course.id} missing gitlab.students_group.group_id and could not find students subgroup")

    return {
        'students_group_id': students_group_id,
        'group_id': gitlab_props.get('group_id')
    }


async def find_existing_repository(
    gitlab: Gitlab,
    namespace_id: int,
    repo_path: str
) -> Optional[Any]:
    """
    Check if a repository already exists in the namespace.
    
    Args:
        gitlab: GitLab client
        namespace_id: The namespace/group ID to search in
        repo_path: The repository path to look for
        
    Returns:
        The existing project if found, None otherwise
    """
    try:
        # Try to get the namespace group
        namespace_group = gitlab.groups.get(namespace_id)
        
        # Method 1: Direct path access
        full_path = f"{namespace_group.full_path}/{repo_path}"
        try:
            project = gitlab.projects.get(full_path.replace('/', '%2F'))
            logger.info(f"Found existing repository: {project.path_with_namespace}")
            return project
        except GitlabGetError:
            # Project does not exist on this path — fall through to search.
            pass
        
        # Method 2: Search projects in namespace by name
        for project in namespace_group.projects.list(search=repo_path, per_page=10):
            if project.path == repo_path:
                return gitlab.projects.get(project.id)
                
    except Exception as e:
        logger.warning(f"Error checking for existing repository: {e}")
    
    return None


async def update_submission_groups(
    db: Session,
    submission_group_ids: list[str],
    repository_info: Dict[str, Any]
) -> list[str]:
    """
    Update submission groups with repository information.
    
    Args:
        db: Database session
        submission_group_ids: List of submission group IDs to update
        repository_info: Repository information to store
        
    Returns:
        List of updated submission group IDs
    """
    from sqlalchemy.orm.attributes import flag_modified
    
    updated_groups = []
    
    if not submission_group_ids:
        logger.info("No submission groups to update")
        return updated_groups
    
    for sg_id in submission_group_ids:
        submission_group = db.query(SubmissionGroup).filter(
            SubmissionGroup.id == sg_id
        ).first()
        
        if submission_group:
            # Get assignment directory from course content's example
            course_content = submission_group.course_content
            assignment_directory = None
            
            # If course content has a deployment with an example, use its directory
            if course_content and course_content.deployment and course_content.deployment.example_version:
                example = course_content.deployment.example_version.example
                if example:
                    assignment_directory = example.directory
            
            # Fallback to course content path if no example directory
            if not assignment_directory and course_content:
                assignment_directory = str(course_content.path) if course_content.path else None
            
            # Update properties
            submission_group.properties = submission_group.properties or {}
            submission_group.properties['gitlab'] = {
                "url": repository_info['url'],
                "full_path": repository_info['full_path'],
                "directory": assignment_directory,
                "web_url": repository_info['web_url'],
                "group_id": repository_info['group_id'],
                "namespace_id": repository_info['namespace_id'],
                "namespace_path": repository_info['namespace_path'],
                "http_url_to_repo": repository_info.get('http_url_to_repo'),  # Properly constructed clone URL
                "ssh_url_to_repo": repository_info.get('ssh_url_to_repo')  # Properly constructed SSH URL
            }
            
            flag_modified(submission_group, "properties")
            db.add(submission_group)
            updated_groups.append(sg_id)
            logger.info(f"Updated submission group {sg_id}")
        else:
            logger.warning(f"Submission group {sg_id} not found")
    
    db.commit()
    return updated_groups


def _resolve_template_project(gitlab: Gitlab, course: Course) -> int:
    """
    Resolve the GitLab project id of the course's ``student-template`` project.

    Single copy of the previously-duplicated resolution logic (was inlined in both
    activities and partly in ``get_course_gitlab_config``). Resolution order:
      1. a stored ``projects.student_template.project_id`` (fast path),
      2. a stored ``projects.student_template.full_path``,
      3. the legacy ``student_template_url`` parsed via regex,
    then a name search scoped to the course group namespace.

    Args:
        gitlab: GitLab client
        course: The course whose properties hold the GitLab configuration

    Returns:
        The GitLab project id of the student-template project

    Raises:
        ValueError: If the project cannot be configured or found
    """
    gitlab_props = (course.properties or {}).get('gitlab', {})
    template_cfg = gitlab_props.get('projects', {}).get('student_template', {})

    # 1) Stored project id (fast path)
    template_project_id = template_cfg.get('project_id')
    if template_project_id:
        return template_project_id

    # 2) Stored full_path, else 3) parse the legacy student_template_url
    template_path = template_cfg.get('full_path')
    if not template_path:
        template_url = gitlab_props.get('student_template_url')
        if template_url:
            match = re.search(r'/([^/]+/[^/]+/[^/]+/student-template)$', template_url)
            if match:
                template_path = match.group(1)

    if not template_path:
        raise ValueError(f"Course {course.id} missing student-template project configuration")

    # Search for the project by name inside the course group namespace
    course_group_id = gitlab_props.get('group_id')
    if not course_group_id:
        raise ValueError(f"Course {course.id} missing gitlab.group_id")

    project_name = template_path.split('/')[-1]  # e.g. 'student-template'
    try:
        projects = gitlab.projects.list(search=project_name, namespace_id=course_group_id)
        for project in projects:
            if project.path == project_name or project.path_with_namespace == template_path:
                template_project = gitlab.projects.get(project.id)
                logger.info(
                    f"Found student-template project with ID {template_project.id} at {template_path}"
                )
                return template_project.id
    except Exception as e:
        raise ValueError(f"Could not find student-template project at {template_path}: {e}")

    raise ValueError(
        f"Student template project '{project_name}' not found in namespace {course_group_id} "
        f"(path: {template_path})"
    )


def _build_repository_info(
    gitlab_url: str,
    project: Any,
    namespace_id: int,
    *,
    team: bool = False,
    directory: Optional[str] = None,
    team_members: Optional[list[str]] = None,
) -> Dict[str, Any]:
    """
    Build the ``repository_info`` dict persisted into entity properties.

    The student and team variants use GENUINELY DIFFERENT, non-overlapping key
    sets that are consumed verbatim downstream and must not be normalized:
      * student -> ``course_member.properties['gitlab']`` (a FLAT dict; ``group_id``
        is the *project* id, ``web_url`` is the GitLab API web_url, ``directory``
        is ``None``);
      * team    -> merged into ``submission_group.properties`` (top-level
        convenience keys + ``team_members`` + a nested ``gitlab`` block whose
        ``group_id`` is the *namespace* id and whose ``web_url`` is constructed).

    Each branch below preserves the ORIGINAL key set, values and insertion order
    of its respective activity byte-for-byte. Parametrized via ``team``.
    """
    ssh_host = gitlab_url.split('://')[1].split('/')[0] if '://' in gitlab_url else 'localhost'
    path_with_namespace = project.path_with_namespace

    if team:
        return {
            "gitlab_project_id": project.id,
            "gitlab_project_path": path_with_namespace,
            # Use properly constructed URLs instead of broken GitLab API fields
            "http_url_to_repo": construct_gitlab_http_url(gitlab_url, path_with_namespace),
            "ssh_url_to_repo": construct_gitlab_ssh_url(path_with_namespace, ssh_host),
            "web_url": construct_gitlab_web_url(gitlab_url, path_with_namespace),
            "team_members": team_members,
            "gitlab": {
                "url": gitlab_url,
                "full_path": path_with_namespace,
                "directory": directory,
                "web_url": construct_gitlab_web_url(gitlab_url, path_with_namespace),
                "group_id": namespace_id,
                "namespace_id": namespace_id,
                "namespace_path": project.namespace['full_path'],
                # Use properly constructed URLs instead of broken GitLab API fields
                "http_url_to_repo": construct_gitlab_http_url(gitlab_url, path_with_namespace),
                "ssh_url_to_repo": construct_gitlab_ssh_url(path_with_namespace, ssh_host),
            },
        }

    namespace_path = (
        project.namespace['full_path']
        if hasattr(project.namespace, '__getitem__')
        else project.namespace.full_path
    )
    return {
        "url": gitlab_url,
        "full_path": path_with_namespace,
        "directory": directory,  # Will be set per assignment
        "web_url": project.web_url,
        "group_id": project.id,
        "namespace_id": namespace_id,
        "namespace_path": namespace_path,
        # Keep for backward compatibility
        "gitlab_project_id": project.id,
        "gitlab_project_path": path_with_namespace,
        # Use properly constructed URLs instead of broken GitLab API fields
        "http_url_to_repo": construct_gitlab_http_url(gitlab_url, path_with_namespace),
        "ssh_url_to_repo": construct_gitlab_ssh_url(path_with_namespace, ssh_host),
    }


async def _unprotect_and_grant(
    gitlab: Gitlab,
    db: Session,
    project: Any,
    member_ids: list[str],
    provider_url: str,
) -> None:
    """
    Post-fork sequence shared by both activities: unprotect the default branches
    so students can push, then grant the given course members maintainer access.

    Unprotect failures are tolerated (the branch may not exist yet); this matches
    the original student activity and harmonizes the team activity (previously the
    team let an unprotect error abort the activity -- a non-fatal condition).
    """
    for branch in ["main", "master"]:
        try:
            gitlab_unprotect_branches(gitlab, project.id, branch)
        except Exception as e:
            logger.debug(f"Could not unprotect {branch} branch: {e}")

    await asyncio.to_thread(
        add_course_members_to_project,
        gitlab, project, member_ids, db,
        provider_url=provider_url,
    )


@activity.defn(name="create_student_repository")
async def create_student_repository(
    course_member_id: str,
    course_id: str,
    submission_group_ids: list[str] = None
) -> Dict[str, Any]:
    """
    Create a single student repository by forking the student-template.
    Updates all submission groups with the same repository information.
    
    Args:
        course_member_id: ID of the course member (student)
        course_id: ID of the course
        submission_group_ids: List of submission group IDs to update with repository info
        
    Returns:
        Dict containing repository information
    """
    with get_db_session() as db:
      try:
        # Get course member and validate
        course_member = db.query(CourseMember).filter(CourseMember.id == course_member_id).first()
        if not course_member:
            raise ValueError(f"Course member {course_member_id} not found")
            
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise ValueError(f"Course {course_id} not found")
        
        organization = db.query(Organization).filter(Organization.id == course.organization_id).first()
        if not organization:
            raise ValueError(f"Organization for course {course_id} not found")
        
        # Get GitLab client and course configuration
        gitlab = get_gitlab_client(organization)
        gitlab_config = get_course_gitlab_config(course, gitlab)
        gitlab_url = organization.properties.get('gitlab', {}).get('url')
        provider_url = gitlab_url  # Provider URL for Account lookup
        
        # Get student-template project ID (single shared resolver)
        student_template_id = _resolve_template_project(gitlab, course)

        # Get user information for repository naming
        user = course_member.user
        username = user.email.split('@')[0] if user.email else f"user_{user.id}"
        
        # Generate repository name and path
        repo_name = username
        repo_path = repo_name.lower().replace(' ', '-').replace('_', '-')
        
        # Get the students group namespace
        gitlab_namespace_id = gitlab_config['students_group_id']
        
        logger.info(f"Checking for existing repository {repo_path} in namespace {gitlab_namespace_id}")
        
        # Check if repository already exists
        existing_project = await find_existing_repository(gitlab, gitlab_namespace_id, repo_path)
        
        # If repository exists, use it; otherwise fork
        if existing_project:
            forked_project = existing_project
            logger.info(f"Using existing repository {repo_path} for {username}")
            
            # Ensure student is maintainer even for existing repo
            try:
                await asyncio.to_thread(
                    add_course_members_to_project,
                    gitlab, forked_project, [course_member_id], db,
                    provider_url=provider_url,
                )
            except Exception as e:
                logger.warning(f"Could not ensure maintainer rights for existing repo: {e}")
        else:
            # Fork the student-template repository
            logger.info(f"Forking template {student_template_id} to {repo_path}")
            try:
                forked_project = await asyncio.to_thread(
                    fork_project_with_polling,
                    gitlab, student_template_id, repo_path, repo_name, gitlab_namespace_id,
                    max_attempts=10, poll_interval=5, initial_wait=2,
                )
            except Exception as fork_error:
                # If fork fails with "already taken", try to find the existing repo
                if "has already been taken" in str(fork_error):
                    logger.warning(f"Repository already exists, searching for it...")
                    forked_project = await find_existing_repository(gitlab, gitlab_namespace_id, repo_path)
                    if not forked_project:
                        raise ValueError(f"Repository {repo_path} exists but cannot be accessed")
                else:
                    raise fork_error

            # Unprotect default branches and grant the student maintainer access
            await _unprotect_and_grant(gitlab, db, forked_project, [course_member_id], provider_url)

        # Prepare repository information (student variant: flat dict)
        repository_info = _build_repository_info(gitlab_url, forked_project, gitlab_namespace_id)

        # Store repository info in course member properties
        from sqlalchemy.orm.attributes import flag_modified
        course_member.properties = course_member.properties or {}
        course_member.properties['gitlab'] = repository_info
        flag_modified(course_member, "properties")
        db.add(course_member)
        db.commit()
        
        # Update submission groups
        updated_submission_groups = await update_submission_groups(
            db, submission_group_ids, repository_info
        )
        
        logger.info(f"Successfully created/configured repository {repo_path} for {username}")
        
        return {
            "success": True,
            "repository": repository_info,
            "course_member_id": course_member_id,
            "submission_groups_updated": updated_submission_groups
        }
            
      except Exception as e:
        logger.error(f"Failed to create student repository: {e}")
        raise e


@activity.defn(name="create_team_repository")
async def create_team_repository(
    submission_group_id: str,
    course_id: str,
    team_members: list[str]
) -> Dict[str, Any]:
    """
    Create a team repository for group assignments.
    
    Args:
        submission_group_id: ID of the submission group
        course_id: ID of the course
        team_members: List of course member IDs in the team
        
    Returns:
        Dict containing repository information
    """
    with get_db_session() as db:
      try:
        # Get course information
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise ValueError(f"Course {course_id} not found")
            
        submission_group = db.query(SubmissionGroup).filter(
            SubmissionGroup.id == submission_group_id
        ).first()
        if not submission_group:
            raise ValueError(f"Submission group {submission_group_id} not found")
        
        # Get the organization to access GitLab credentials
        organization = db.query(Organization).filter(Organization.id == course.organization_id).first()
        if not organization:
            raise ValueError(f"Organization for course {course_id} not found")
        
        # Get GitLab client and URL from organization (shared helper)
        gitlab = get_gitlab_client(organization)
        gitlab_url = organization.properties.get('gitlab', {}).get('url')

        # Get GitLab properties
        course_properties = course.properties or {}
        gitlab_props = course_properties.get('gitlab', {})
        gitlab_namespace_id = gitlab_props.get('students_group', {}).get('group_id')
        
        if not gitlab_namespace_id:
            raise ValueError(f"Course {course_id} missing gitlab.students_group.group_id")
        
        # Resolve the student-template project id (single shared resolver)
        student_template_id = _resolve_template_project(gitlab, course)

        # Get team member names for repository naming
        team_name_parts = []
        for member_id in team_members[:3]:  # Use first 3 members for naming
            member = db.query(CourseMember).filter(CourseMember.id == member_id).first()
            if member and member.user:
                username = member.user.email.split('@')[0] if member.user.email else f"user_{member.user.id}"
                team_name_parts.append(username)
                
        team_name = "-".join(team_name_parts) if team_name_parts else f"team-{submission_group_id[:8]}"
        
        # Generate repository name and path (just team-{team_name})
        repo_name = f"team-{team_name}"
        repo_path = repo_name.lower().replace(' ', '-').replace('_', '-')[:63]  # GitLab path limit
        
        logger.info(f"Creating team repository {repo_path} for {len(team_members)} members")
        
        # Fork the student-template repository with polling
        team_project = await asyncio.to_thread(
            fork_project_with_polling,
            gitlab, student_template_id, repo_path, repo_name, gitlab_namespace_id,
            max_attempts=10, poll_interval=5, initial_wait=2,
        )

        # Unprotect default branches and grant the team maintainer access
        await _unprotect_and_grant(gitlab, db, team_project, team_members, gitlab_url)

        # Get assignment directory from course content's example
        course_content = submission_group.course_content
        assignment_directory = None
        
        # If course content has a deployment with an example, use its directory
        if course_content and course_content.deployment and course_content.deployment.example_version:
            example = course_content.deployment.example_version.example
            if example:
                assignment_directory = example.directory
        
        # Fallback to course content path if no example directory
        if not assignment_directory and course_content:
            assignment_directory = str(course_content.path) if course_content.path else None
        
        # Update submission group with repository information (team variant:
        # nested dict with top-level convenience keys + team_members)
        repository_info = _build_repository_info(
            gitlab_url, team_project, gitlab_namespace_id,
            team=True, directory=assignment_directory, team_members=team_members,
        )

        submission_group.properties = submission_group.properties or {}
        submission_group.properties.update(repository_info)
        db.commit()
        
        logger.info(f"Successfully created team repository {repo_path}")
        
        return {
            "success": True,
            "repository": repository_info,
            "submission_group_id": submission_group_id,
            "team_size": len(team_members)
        }
        
      except Exception as e:
        logger.error(f"Failed to create team repository: {e}")
        raise e


@register_task
@workflow.defn(name="StudentRepositoryCreationWorkflow", sandboxed=False)
class StudentRepositoryCreationWorkflow(BaseWorkflow):
    """
    Workflow to create student repositories when they join a course.
    Handles both individual and team repositories.
    """
    
    @classmethod
    def get_name(cls) -> str:
        """Get the workflow name."""
        return "StudentRepositoryCreationWorkflow"
    
    @workflow.run
    async def run(self, params: Dict[str, Any]) -> WorkflowResult:
        """
        Execute the student repository creation workflow.
        
        Expected params:
        - course_member_id: ID of the course member
        - course_id: ID of the course
        - submission_group_ids: List of submission group IDs to process
        - is_team: Whether this is for team repositories
        - team_members: List of member IDs (for team repos)
        """
        retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=10),
            backoff_coefficient=2
        )
        
        try:
            course_member_id = params.get('course_member_id')
            course_id = params.get('course_id')
            submission_group_ids = params.get('submission_group_ids', [])
            is_team = params.get('is_team', False)
            team_members = params.get('team_members', [])
            
            results = []
            
            if is_team:
                # Create team repositories
                for submission_group_id in submission_group_ids:
                    result = await workflow.execute_activity(
                        create_team_repository,
                        args=[submission_group_id, course_id, team_members],
                        retry_policy=retry_policy,
                        start_to_close_timeout=timedelta(minutes=5)
                    )
                    results.append(result)
            else:
                # Create ONE student repository (not one per submission group!)
                result = await workflow.execute_activity(
                    create_student_repository,
                    args=[course_member_id, course_id, submission_group_ids],  # Pass ALL submission group IDs
                    retry_policy=retry_policy,
                    start_to_close_timeout=timedelta(minutes=5)
                )
                results.append(result)
                    
            return WorkflowResult(
                status="completed",
                result={"message": f"Created {len(results)} repositories", "repositories": results},
                metadata={"repository_count": len(results)}
            )
            
        except Exception as e:
            logger.error(f"Student repository creation workflow failed: {e}")
            return WorkflowResult(
                status="failed",
                result=None,
                error=str(e),
                metadata={"error_details": str(e)}
            )

ACTIVITIES = [
    create_student_repository,
    create_team_repository,
]
