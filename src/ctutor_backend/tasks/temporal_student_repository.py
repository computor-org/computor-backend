"""
Temporal workflows for creating and managing student repositories.
This workflow handles forking the student-template repository when students join a course.
"""
import logging
import json
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
from ..database import get_db
from ..model.course import Course, CourseMember, SubmissionGroup, SubmissionGroupMember
from ..gitlab_utils import construct_gitlab_http_url, construct_gitlab_ssh_url, construct_gitlab_web_url
from ..model.organization import Organization
from ..interface.tokens import decrypt_api_key
from ..gitlab_utils import gitlab_fork_project, gitlab_unprotect_branches

logger = logging.getLogger(__name__)


async def fork_project_with_polling(
    gitlab: Gitlab,
    source_project_id: int,
    dest_path: str,
    dest_name: str,
    namespace_id: int,
    max_attempts: int = 10,
    poll_interval: int = 5,
    initial_wait: int = 2
) -> Any:
    """
    Fork a GitLab project and poll for completion.
    
    Args:
        gitlab: GitLab client instance
        source_project_id: ID of the project to fork
        dest_path: Path for the forked project
        dest_name: Name for the forked project
        namespace_id: GitLab namespace ID where to create the fork
        max_attempts: Maximum number of polling attempts
        poll_interval: Seconds between polling attempts
        initial_wait: Initial wait before starting to poll
        
    Returns:
        The forked GitLab project object
        
    Raises:
        ValueError: If the fork is not found after max_attempts
    """
    import asyncio
    
    # Initiate the fork
    gitlab_fork_project(
        gitlab=gitlab,
        fork_id=source_project_id,
        dest_path=dest_path,
        dest_name=dest_name,
        namespace_id=namespace_id
    )
    
    # Initial wait before polling
    await asyncio.sleep(initial_wait)
    
    # Poll for fork completion
    forked_project = None
    for attempt in range(max_attempts):
        # Find the forked project
        projects = gitlab.groups.get(namespace_id).projects.list(search=dest_path)
        for project in projects:
            if project.path == dest_path:
                forked_project = gitlab.projects.get(project.id)
                break
        
        if forked_project:
            logger.info(f"Fork completed after {attempt + 1} attempt(s)")
            return forked_project
            
        if attempt < max_attempts - 1:
            logger.info(f"Fork not ready yet, waiting {poll_interval} seconds (attempt {attempt + 1}/{max_attempts})")
            await asyncio.sleep(poll_interval)
            
    raise ValueError(f"Forked project {dest_path} not found after {max_attempts} attempts")


async def add_members_to_project(
    gitlab: Gitlab,
    project,
    member_ids: list[str],
    db: Session,
    access_level: int = 40
) -> None:
    """
    Add course members as maintainers to a GitLab project.
    
    Args:
        gitlab: GitLab client instance
        project: GitLab project object
        member_ids: List of course member IDs to add
        db: Database session
        access_level: GitLab access level (40 = Maintainer)
    """
    for member_id in member_ids:
        member = db.query(CourseMember).filter(CourseMember.id == member_id).first()
        if not member or not member.user:
            continue
            
        gitlab_user_id = None
        member_props = member.properties or {}
        
        # Get or find GitLab user ID
        if member_props.get('gitlab_user_id'):
            gitlab_user_id = member_props['gitlab_user_id']
        elif member.user.email:
            # Try to find by email
            try:
                users = gitlab.users.list(search=member.user.email)
                if users:
                    gitlab_user_id = users[0].id
                    # Store for future use
                    member.properties = member_props
                    member.properties['gitlab_user_id'] = gitlab_user_id
                    db.add(member)
                    db.commit()
            except Exception as e:
                logger.warning(f"Could not find GitLab user for {member.user.email}: {e}")
        
        if gitlab_user_id:
            try:
                project.members.create({
                    'user_id': gitlab_user_id,
                    'access_level': access_level
                })
                logger.info(f"Added user {gitlab_user_id} as maintainer to project {project.id}")
            except Exception as e:
                logger.warning(f"Could not add member {gitlab_user_id} to project: {e}")


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
    
    gitlab_token = decrypt_api_key(gitlab_token_encrypted)
    
    # Transform URL for Docker environment if needed
    from ..utils.docker_utils import transform_localhost_url
    api_url = transform_localhost_url(gitlab_url)
    
    return Gitlab(api_url, private_token=gitlab_token)


def get_course_gitlab_config(course: Course, gitlab: Optional[Gitlab] = None) -> Dict[str, Any]:
    """
    Extract GitLab configuration from course properties.
    
    Args:
        course: The course object
        gitlab: Optional GitLab client for finding missing groups
        
    Returns:
        GitLab configuration dictionary
        
    Raises:
        ValueError: If required GitLab configuration is missing
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
    
    # Get template project ID (should be stored directly)
    template_project_id = gitlab_props.get('projects', {}).get('student_template', {}).get('project_id')
    if not template_project_id:
        # Fallback to full_path for backward compatibility
        template_path = gitlab_props.get('projects', {}).get('student_template', {}).get('full_path')
        if not template_path:
            # Last resort: check for student_template_url
            template_url = gitlab_props.get('student_template_url')
            if template_url:
                # Extract path from URL
                import re
                match = re.search(r'/([^/]+/[^/]+/[^/]+/student-template)$', template_url)
                if match:
                    template_path = match.group(1)
            
            if not template_path:
                raise ValueError(f"Course {course.id} missing student-template project configuration")
        template_project_id = None  # Will need to look it up
    
    return {
        'students_group_id': students_group_id,
        'template_project_id': template_project_id,
        'template_path': gitlab_props.get('projects', {}).get('student_template', {}).get('full_path') or template_path,
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
        except:
            pass
        
        # Method 2: List projects in namespace
        for project in namespace_group.projects.list(all=True):
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
    db = next(get_db())
    
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
        
        # Get student-template project ID
        student_template_id = gitlab_config.get('template_project_id')
        
        # If not stored as ID, look it up from path (backward compatibility)
        if not student_template_id:
            template_path = gitlab_config.get('template_path')
            if not template_path:
                raise ValueError(f"Course {course_id} missing student-template project configuration")
            
            # Look up project by searching in the course namespace
            try:
                # Extract the project name from the full path
                project_name = template_path.split('/')[-1]  # 'student-template'
                course_group_id = gitlab_config.get('group_id')
                
                if not course_group_id:
                    raise ValueError(f"Course {course_id} missing gitlab.group_id")
                
                # Search for the project in the course namespace
                projects = gitlab.projects.list(
                    search=project_name,
                    search_namespaces=True,
                    owned=True,
                    all=True
                )
                
                # Find the exact match by full path
                student_template_project = None
                for project in projects:
                    if project.path_with_namespace == template_path:
                        student_template_project = project
                        break
                
                if not student_template_project:
                    raise ValueError(f"Student template project not found at path: {template_path}")
                
                student_template_id = student_template_project.id
                logger.info(f"Found student-template project with ID {student_template_id} at {template_path}")
            except Exception as e:
                raise ValueError(f"Could not find student-template project at {template_path}: {e}")
            
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
                await add_members_to_project(
                    gitlab=gitlab,
                    project=forked_project,
                    member_ids=[course_member_id],
                    db=db
                )
            except Exception as e:
                logger.warning(f"Could not ensure maintainer rights for existing repo: {e}")
        else:
            # Fork the student-template repository
            logger.info(f"Forking template {student_template_id} to {repo_path}")
            try:
                forked_project = await fork_project_with_polling(
                    gitlab=gitlab,
                    source_project_id=student_template_id,
                    dest_path=repo_path,
                    dest_name=repo_name,
                    namespace_id=gitlab_namespace_id
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
                
            # Unprotect branches to allow student pushes
            for branch in ["main", "master"]:
                try:
                    gitlab_unprotect_branches(gitlab, forked_project.id, branch)
                except Exception as e:
                    logger.debug(f"Could not unprotect {branch} branch: {e}")
                
            # Add student as maintainer of the repository
            await add_members_to_project(
                gitlab=gitlab,
                project=forked_project,
                member_ids=[course_member_id],
                db=db
            )
        
        # Prepare repository information
        repository_info = {
            "url": gitlab_url,
            "full_path": forked_project.path_with_namespace,
            "directory": None,  # Will be set per assignment
            "web_url": forked_project.web_url,
            "group_id": forked_project.id,
            "namespace_id": gitlab_namespace_id,
            "namespace_path": forked_project.namespace['full_path'] if hasattr(forked_project.namespace, '__getitem__') else forked_project.namespace.full_path,
            # Keep for backward compatibility
            "gitlab_project_id": forked_project.id,
            "gitlab_project_path": forked_project.path_with_namespace,
            # Use properly constructed URLs instead of broken GitLab API fields
            "http_url_to_repo": construct_gitlab_http_url(gitlab_url, forked_project.path_with_namespace),
            "ssh_url_to_repo": construct_gitlab_ssh_url(forked_project.path_with_namespace, gitlab_url.split('://')[1].split('/')[0] if '://' in gitlab_url else 'localhost')
        }
        
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
    finally:
        db.close()


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
    db = next(get_db())
    
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
        
        # Get GitLab credentials from organization
        org_properties = organization.properties or {}
        gitlab_config = org_properties.get('gitlab', {})
        gitlab_url = gitlab_config.get('url')
        gitlab_token_encrypted = gitlab_config.get('token')
        
        if not gitlab_url or not gitlab_token_encrypted:
            raise ValueError(f"Organization {organization.id} missing GitLab configuration")
        
        # Decrypt the GitLab token
        gitlab_token = decrypt_api_key(gitlab_token_encrypted)
        
        # Transform URL for Docker environment if needed
        from ..utils.docker_utils import transform_localhost_url
        api_url = transform_localhost_url(gitlab_url)
        
        # Initialize GitLab client with organization's credentials
        gitlab = Gitlab(api_url, private_token=gitlab_token)
            
        # Get GitLab properties
        course_properties = course.properties or {}
        gitlab_props = course_properties.get('gitlab', {})
        gitlab_namespace_id = gitlab_props.get('students_group', {}).get('group_id')
        
        if not gitlab_namespace_id:
            raise ValueError(f"Course {course_id} missing gitlab.students_group.group_id")
        
        # Get student-template project path from course properties
        student_template_path = gitlab_props.get('projects', {}).get('student_template', {}).get('full_path')
        if not student_template_path:
            # Fallback to URL parsing
            student_template_url = gitlab_props.get('student_template_url')
            if student_template_url:
                # Extract path from URL
                import re
                match = re.search(r'/([^/]+/[^/]+/[^/]+/student-template)$', student_template_url)
                if match:
                    student_template_path = match.group(1)
        
        if not student_template_path:
            raise ValueError(f"Course {course_id} missing student-template project path")
        
        # Find the student-template project
        try:
            # Extract project name and namespace from path
            path_parts = student_template_path.split('/')
            if len(path_parts) < 2:
                raise ValueError(f"Invalid student template path: {student_template_path}")
            
            project_name = path_parts[-1]  # Last part is the project name
            
            # Get the course group ID to search in the correct namespace
            course_group_id = gitlab_props.get('group_id')
            if not course_group_id:
                raise ValueError(f"Course {course_id} missing gitlab.group_id")
            
            # Search for the project in the course namespace
            projects = gitlab.projects.list(
                search=project_name,
                namespace_id=course_group_id
            )
            
            student_template_project = None
            for project in projects:
                if project.path == project_name:
                    student_template_project = gitlab.projects.get(project.id)
                    break
            
            if not student_template_project:
                raise ValueError(f"Student template project '{project_name}' not found in namespace {course_group_id}")
            
            student_template_id = student_template_project.id
        except Exception as e:
            raise ValueError(f"Could not find student-template project at {student_template_path}: {e}")
            
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
        team_project = await fork_project_with_polling(
            gitlab=gitlab,
            source_project_id=student_template_id,
            dest_path=repo_path,
            dest_name=repo_name,
            namespace_id=gitlab_namespace_id
        )
            
        # Unprotect branches
        gitlab_unprotect_branches(gitlab, team_project.id, "main")
        gitlab_unprotect_branches(gitlab, team_project.id, "master")
        
        # Add team members as maintainers
        await add_members_to_project(
            gitlab=gitlab,
            project=team_project,
            member_ids=team_members,
            db=db
        )
                    
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
        
        # Update submission group with repository information
        repository_info = {
            "gitlab_project_id": team_project.id,
            "gitlab_project_path": team_project.path_with_namespace,
            # Use properly constructed URLs instead of broken GitLab API fields
            "http_url_to_repo": construct_gitlab_http_url(gitlab_url, team_project.path_with_namespace),
            "ssh_url_to_repo": construct_gitlab_ssh_url(team_project.path_with_namespace, gitlab_url.split('://')[1].split('/')[0] if '://' in gitlab_url else 'localhost'),
            "web_url": construct_gitlab_web_url(gitlab_url, team_project.path_with_namespace),
            "team_members": team_members,
            "gitlab": {
                "url": gitlab_url,
                "full_path": team_project.path_with_namespace,
                "directory": assignment_directory,
                "web_url": construct_gitlab_web_url(gitlab_url, team_project.path_with_namespace),
                "group_id": gitlab_namespace_id,
                "namespace_id": gitlab_namespace_id,
                "namespace_path": team_project.namespace['full_path'],
                # Use properly constructed URLs instead of broken GitLab API fields
                "http_url_to_repo": construct_gitlab_http_url(gitlab_url, team_project.path_with_namespace),
                "ssh_url_to_repo": construct_gitlab_ssh_url(team_project.path_with_namespace, gitlab_url.split('://')[1].split('/')[0] if '://' in gitlab_url else 'localhost')
            }
        }
        
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
    finally:
        db.close()


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
                status="success",
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