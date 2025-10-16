"""
Temporal workflows for generating student templates from Example Library.
Version 2: Fixed deployment status handling and sandbox restrictions.
"""
import logging
from datetime import timedelta
from typing import Dict, Any, List

from temporalio import workflow, activity
from temporalio.common import RetryPolicy

from .temporal_base import BaseWorkflow, WorkflowResult
from .registry import register_task

logger = logging.getLogger(__name__)


async def process_example_for_student_template_v2(
    example_files: Dict[str, bytes],
    target_path: Any,  # Path object
    course_content: Any,
    version: Any
) -> Dict[str, Any]:
    """
    Process example files for student template generation.
    Uses meta.yaml to determine which files to include.
    """
    import yaml
    from pathlib import Path
    
    try:
        # Create target directory
        target_path.mkdir(parents=True, exist_ok=True)
        
        # Parse meta.yaml if it exists
        meta_yaml = None
        if 'meta.yaml' in example_files:
            try:
                meta_yaml = yaml.safe_load(example_files['meta.yaml'])
            except Exception as e:
                logger.error(f"Failed to parse meta.yaml: {e}")
        
        # Process content directory files
        for filename, content in example_files.items():
            if filename.startswith('content/'):
                # Handle index*.md files specially - rename to README*.md
                if filename.startswith('content/index'):
                    # Handle index.md -> README.md
                    if filename == 'content/index.md':
                        readme_path = target_path / 'README.md'
                        readme_path.write_bytes(content)
                    # Handle index_<lang>.md -> README_<lang>.md
                    elif filename.startswith('content/index_') and filename.endswith('.md'):
                        # Extract language suffix
                        lang_suffix = filename[len('content/index'):-3]  # Gets '_de' from 'content/index_de.md'
                        readme_filename = f'README{lang_suffix}.md'
                        readme_path = target_path / readme_filename
                        readme_path.write_bytes(content)
                # Copy all other content files (mediaFiles, etc.) preserving structure
                else:
                    # Remove 'content/' prefix and copy to assignment root
                    relative_path = filename.replace('content/', '', 1)
                    file_path = target_path / relative_path
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_bytes(content)
        
        if meta_yaml:
            properties = meta_yaml.get('properties', {})
            
            # Process additionalFiles - copy to assignment root
            additional_files = properties.get('additionalFiles', [])
            for file_name in additional_files:
                if file_name in example_files:
                    # Copy to root of assignment directory
                    file_path = target_path / Path(file_name).name  # Use only filename, not path
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_bytes(example_files[file_name])
            
            # Process studentSubmissionFiles - ensure all required files exist
            # Use content from studentTemplates when available, otherwise create empty
            submission_files = properties.get('studentSubmissionFiles', [])
            student_templates = properties.get('studentTemplates', [])
            
            # Build a map of template filenames to their content
            template_content_map = {}
            for template_path in student_templates:
                # Try to find the template file in example_files
                file_content = None
                actual_path = None
                
                if template_path in example_files:
                    file_content = example_files[template_path]
                    actual_path = template_path
                else:
                    # Try to find by filename
                    filename = Path(template_path).name
                    for file_path, content in example_files.items():
                        if Path(file_path).name == filename:
                            # Prefer paths containing 'studentTemplate'
                            if 'studentTemplate' in file_path:
                                file_content = content
                                actual_path = file_path
                                break
                            elif file_content is None:
                                file_content = content
                                actual_path = file_path
                
                if file_content is not None:
                    # Store the content mapped to just the filename
                    filename = Path(template_path).name
                    template_content_map[filename] = file_content
                    logger.info(f"Found template content for: {filename} from {actual_path}")
                else:
                    logger.warning(f"Student template file not found: {template_path}")
            
            # Now create all studentSubmissionFiles
            for submission_file in submission_files:
                submission_path = target_path / submission_file
                submission_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Check if we have template content for this file
                if submission_file in template_content_map:
                    # Use template content
                    submission_path.write_bytes(template_content_map[submission_file])
                    logger.info(f"Created {submission_file} from template")
                else:
                    # Create empty file
                    submission_path.write_text('')
                    logger.info(f"Created empty file: {submission_file}")
        else:
            # No meta.yaml - fallback processing
            logger.warning(f"No meta.yaml found for {course_content.path}, using fallback processing")
            for filename, content in example_files.items():
                # Skip test files and meta files
                if not filename.startswith('test') and not filename.endswith('_test.py') and filename != 'meta.yaml':
                    file_path = target_path / filename
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_bytes(content)
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Failed to process example content {course_content.path}: {e}")
        return {"success": False, "error": str(e)}


async def generate_assignments_repository(
    course_id: str,
    assignments_url: str,
    course_contents: List[Any],
    course: Any,
    organization: Any,
    gitlab_token: str,
    db: Any
) -> Dict[str, Any]:
    """
    Generate assignments repository with full example content (unmodified).
    This serves as the reference repository for lecturers and tutors.
    
    Args:
        course_id: Course ID
        assignments_url: GitLab URL for assignments repository
        course_contents: List of course contents with deployments
        course: Course model instance
        organization: Organization model instance
        gitlab_token: GitLab authentication token
        db: Database session
    
    Returns:
        Dict with success status and details
    """
    import git
    import os
    import tempfile
    import shutil
    from pathlib import Path
    from datetime import datetime, timezone
    from ..utils.docker_utils import transform_localhost_url
    
    try:
        logger.info(f"Generating assignments repository for course {course_id}")
        
        # Transform URL for Docker environment
        assignments_url = transform_localhost_url(assignments_url)
        logger.info(f"Using assignments URL: {assignments_url}")
        
        # Create temporary directories
        temp_dir = tempfile.mkdtemp(prefix='assignments-gen-')
        assignments_repo_path = os.path.join(temp_dir, 'assignments')
        
        # Clone or create assignments repository
        try:
            if gitlab_token and 'http' in assignments_url:
                from urllib.parse import urlparse, urlunparse
                parsed = urlparse(assignments_url)
                auth_netloc = f"oauth2:{gitlab_token}@{parsed.netloc}"
                auth_url = urlunparse((parsed.scheme, auth_netloc, parsed.path, 
                                     parsed.params, parsed.query, parsed.fragment))
                assignments_repo = git.Repo.clone_from(auth_url, assignments_repo_path)
            else:
                assignments_repo = git.Repo.clone_from(assignments_url, assignments_repo_path)
                
            logger.info(f"Successfully cloned assignments repository to {assignments_repo_path}")
        except Exception as e:
            logger.error(f"Failed to clone assignments repository: {e}")
            return {"success": False, "error": f"Failed to clone repository: {str(e)}"}
        
        # Clear existing content except .git
        for item in os.listdir(assignments_repo_path):
            if item == '.git':
                continue
            item_path = os.path.join(assignments_repo_path, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
        
        logger.info(f"Cleared existing content in assignments repository")
        
        processed_count = 0
        errors = []
        
        # Process each course content with full example data
        for content in course_contents:
            try:
                if not content.deployment or not content.deployment.example_version:
                    logger.warning(f"CourseContent {content.path} has no deployment")
                    continue
                
                example_version = content.deployment.example_version
                example = example_version.example
                
                if not example:
                    logger.warning(f"CourseContent {content.path} deployment has no example")
                    continue
                
                logger.info(f"Processing assignment content: {content.path}, example: {example.identifier}")
                
                # Download example files from MinIO
                example_files = await download_example_files(example.repository, example_version)
                
                # For assignments repository, copy ALL files unmodified to preserve full example
                content_path_str = str(example.identifier)
                assignment_path = Path(assignments_repo_path) / content_path_str
                
                # Create target directory
                assignment_path.mkdir(parents=True, exist_ok=True)
                
                # Copy ALL files unmodified (including solutions, meta.yaml, tests, etc.)
                for filename, file_content in example_files.items():
                    file_path = assignment_path / filename
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_bytes(file_content)
                
                logger.info(f"Copied {len(example_files)} files to {content_path_str}")
                processed_count += 1
                
            except Exception as e:
                error_msg = f"Failed to process assignment content {content.path}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Create README for assignments repository
        readme_content = f"""# Assignments Repository - {course.title}

This repository contains the complete example content with solutions for course assignments.

## Purpose
- **Reference repository** for lecturers and tutors
- Contains **full example content** including solutions, test files, and metadata
- **Do not share** with students (contains solutions)

## Usage
- Lecturers: Edit and improve examples
- Tutors: Reference for grading and student assistance
- Generated automatically from Example Library

## Contents
"""
        
        # Add content listing
        for content in course_contents:
            if content.deployment and content.deployment.example_version:
                example = content.deployment.example_version.example
                if example:
                    readme_content += f"- `{example.identifier}/` - {content.title}\n"
        
        readme_content += f"""
---
*Last updated: {datetime.now(timezone.utc).isoformat()}*
*Generated by Computor Example Library*
"""
        
        readme_path = os.path.join(assignments_repo_path, 'README.md')
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        # Configure git for commits
        git_email = os.environ.get('SYSTEM_GIT_EMAIL', 'worker@computor.local')
        git_name = os.environ.get('SYSTEM_GIT_NAME', 'Computor Worker')
        assignments_repo.git.config('user.email', git_email)
        assignments_repo.git.config('user.name', git_name)
        
        # Commit and push changes
        assignments_repo.git.add('.')
        if assignments_repo.is_dirty(untracked_files=True):
            commit_message = f"Update assignments repository for {course.title}\n\n" \
                           f"Processed {processed_count} examples from Example Library\n" \
                           f"Generated: {datetime.now(timezone.utc).isoformat()}"
            assignments_repo.index.commit(commit_message)
            
            # Push to remote
            try:
                if gitlab_token and 'http' in assignments_url:
                    # Configure token for push
                    from urllib.parse import urlparse, urlunparse
                    parsed = urlparse(assignments_url)
                    auth_netloc = f"oauth2:{gitlab_token}@{parsed.netloc}"
                    auth_url = urlunparse((parsed.scheme, auth_netloc, parsed.path,
                                         parsed.params, parsed.query, parsed.fragment))
                    assignments_repo.remotes.origin.set_url(auth_url)
                
                assignments_repo.remotes.origin.push('main', force=True)
                logger.info(f"Successfully pushed assignments repository with {processed_count} examples")
            except Exception as push_error:
                logger.error(f"Failed to push assignments repository: {push_error}")
                return {"success": False, "error": f"Failed to push: {str(push_error)}"}
        else:
            logger.info("No changes to commit in assignments repository")
        
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        return {
            "success": True,
            "processed_count": processed_count,
            "errors": errors,
            "message": f"Generated assignments repository with {processed_count} examples"
        }
        
    except Exception as e:
        logger.error(f"Failed to generate assignments repository: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


async def download_example_files(repository: Any, version: Any) -> Dict[str, bytes]:
    """
    Download example files from repository based on its source type.
    
    Args:
        repository: ExampleRepository with source type information
        version: ExampleVersion with storage path information
        
    Returns:
        Dictionary mapping file paths to their content
        
    Raises:
        NotImplementedError: For unsupported repository types
        ValueError: For invalid source types
    """
    if repository.source_type == 'git':
        return await download_example_from_git(repository, version)
    elif repository.source_type in ['minio', 's3']:
        return await download_example_from_object_storage(repository, version)
    else:
        raise ValueError(f"Unsupported source type: {repository.source_type}")


async def download_example_from_git(repository: Any, version: Any) -> Dict[str, bytes]:
    # """Download example files from Git repository."""
    # import os
    # import tempfile
    # import shutil
    # import git
    
    # files = {}
    # temp_dir = tempfile.mkdtemp()
    
    # try:
    #     repo = git.Repo.clone_from(repository.url, temp_dir, branch=version.version_tag)
        
    #     for root, dirs, file_list in os.walk(temp_dir):
    #         # Skip .git directory
    #         if '.git' in dirs:
    #             dirs.remove('.git')
            
    #         for file_name in file_list:
    #             file_path = os.path.join(root, file_name)
    #             relative_path = os.path.relpath(file_path, temp_dir)
                
    #             with open(file_path, 'rb') as f:
    #                 files[relative_path] = f.read()
        
    #     return files
    # finally:
    #     shutil.rmtree(temp_dir, ignore_errors=True)
    logger.error(f"Git source type not implemented for repository {repository.name}")
    raise NotImplementedError(f"Git source type is not yet implemented for repository '{repository.name}'")


async def download_example_from_object_storage(
    repository: Any, 
    version: Any
) -> Dict[str, bytes]:
    """
    Download example files from MinIO/S3 object storage.
    
    Args:
        repository: ExampleRepository with source_type in ['minio', 's3']
        version: ExampleVersion with storage path information
        
    Returns:
        Dictionary mapping file paths to their content
    """
    from ..services.storage_service import StorageService
    
    # Initialize storage service
    storage_service = StorageService()
    
    storage_path = version.storage_path
    bucket_name = repository.source_url  # Use repository's source_url as bucket name
    prefix = storage_path.strip('/')
    
    logger.info(f"Downloading from {repository.source_type} bucket: {bucket_name}, path: {storage_path}")
    
    # Download all files for this example
    example_files = {}
    objects = await storage_service.list_objects(
        prefix=prefix,
        bucket_name=bucket_name
    )
    
    for obj in objects:
        try:
            # Download file content
            file_data = await storage_service.download_file(
                object_key=obj.object_name,
                bucket_name=bucket_name
            )
            
            # Get relative path within example
            relative_path = obj.object_name
            if prefix:
                relative_path = obj.object_name.replace(prefix, '').lstrip('/')
            
            example_files[relative_path] = file_data
        except Exception as e:
            logger.error(f"Failed to download {obj.object_name}: {e}")
    
    return example_files


# Activities
@activity.defn(name="generate_student_template_activity_v2")
async def generate_student_template_activity_v2(
    course_id: str,
    student_template_url: str,
    assignments_url: str = None,
    workflow_id: str = None,
    force_redeploy: bool = False,
    release: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    """
    Generate student template repository from examples assigned to course content.
    
    This activity:
    1. Sets all assigned deployments to 'deploying' status (or resets deployed if force_redeploy)
    2. Clones/creates the student-template repository
    3. Downloads example files from MinIO/S3
    4. Processes examples (removes solutions, adds README)
    5. Commits and pushes to GitLab
    6. Updates deployment status and tracking
    7. If assignments_url provided, also creates assignments repository with full examples
    
    Args:
        course_id: Course to generate template for
        student_template_url: GitLab URL of student template repository
        assignments_url: Optional GitLab URL of assignments repository (full examples)
        workflow_id: Temporal workflow ID for tracking
        force_redeploy: If True, redeploy already deployed content (default: False)
    
    Returns:
        Dict with success status and details
    """
    # Import all SQLAlchemy models and database dependencies inside activity
    import git
    import os
    import tempfile
    import shutil
    from pathlib import Path
    from datetime import datetime, timezone
    from sqlalchemy.orm import joinedload
    from sqlalchemy import and_
    from ..utils.docker_utils import transform_localhost_url
    from ..database import get_db
    from ..model.course import Course, CourseContent
    from ..model.example import Example, ExampleVersion, ExampleRepository
    from ..model.deployment import CourseContentDeployment, DeploymentHistory
    from ..model.execution import ExecutionBackend
    from ..services.storage_service import StorageService
    
    db_gen = next(get_db())
    db = db_gen
    
    try:
        # First, update all assigned deployments to 'deploying' status
        # Determine which deployment statuses to process
        if force_redeploy:
            # Include already deployed content for redeployment
            statuses_to_process = ["pending", "failed", "deployed"]
            logger.info(f"Force redeploy enabled - will reprocess deployed content for course {course_id}")
        else:
            # Normal mode - only process pending and failed
            statuses_to_process = ["pending", "failed"]
            logger.info(f"Updating deployments to 'deploying' status for course {course_id}")
        
        # If a release selection is provided, restrict to selected contents; else fallback to status-based selection
        selected_course_content_ids: List[str] = []
        if release:
            ids = release.get("course_content_ids") or []
            if ids:
                selected_course_content_ids = ids
            elif release.get("parent_id"):
                parent_id = release.get("parent_id")
                include_desc = bool(release.get("include_descendants", True))
                parent = db.query(CourseContent).filter(CourseContent.id == parent_id).first()
                if parent:
                    q = db.query(CourseContent).filter(CourseContent.course_id == course_id)
                    if include_desc:
                        q = q.filter(CourseContent.path.descendant_of(parent.path))
                    else:
                        q = q.filter(CourseContent.id == parent.id)
                    selected_course_content_ids = [str(cc.id) for cc in q.all()]
            elif release.get("all"):
                selected_course_content_ids = [str(cc.id) for (cc,) in db.query(CourseContent.id).filter(CourseContent.course_id == course_id).all()]

        if selected_course_content_ids:
            deployments_to_process = db.query(CourseContentDeployment).join(CourseContent).filter(
                and_(
                    CourseContent.course_id == course_id,
                    CourseContent.id.in_(selected_course_content_ids)
                )
            ).all()
        else:
            deployments_to_process = db.query(CourseContentDeployment).join(
                CourseContent
            ).filter(
                and_(
                    CourseContent.course_id == course_id,
                    CourseContentDeployment.deployment_status.in_(statuses_to_process)
                )
            ).all()
        
        # Update all to 'deploying' and add history
        for deployment in deployments_to_process:
            # Track if this is a redeploy
            was_deployed = deployment.deployment_status == "deployed"
            
            deployment.deployment_status = "deploying"
            deployment.last_attempt_at = datetime.now(timezone.utc)
            if workflow_id:
                deployment.workflow_id = workflow_id
            
            history = DeploymentHistory(
                deployment_id=deployment.id,
                action="deploying",
                example_version_id=deployment.example_version_id,
                workflow_id=workflow_id,
            )
            db.add(history)
        
        db.commit()
        
        logger.info(f"Updated {len(deployments_to_process)} deployments to 'deploying' status")
        
        # Transform localhost URLs for Docker environments
        student_template_url = transform_localhost_url(student_template_url)
        logger.info(f"Using student template URL: {student_template_url}")

        # Get course details
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise ValueError(f"Course {course_id} not found")
        
        organization = course.organization
        
        # # Get organization directly using the foreign key relationship
        # organization = db.query(Organization).filter(Organization.id == course.organization_id).first()
        # if not organization:
        #     raise ValueError(f"Organization not found for course {course_id}. Organization ID: {course.organization_id}")
        
        # Get GitLab token from organization properties
        gitlab_token = None
        if organization.properties and 'gitlab' in organization.properties:
            gitlab_config = organization.properties.get('gitlab', {})
            encrypted_token = gitlab_config.get('token')  # Use 'token' field as defined in GitLabConfig
            
            if encrypted_token:
                # Decrypt the GitLab token
                from computor_types.tokens import decrypt_api_key
                try:
                    gitlab_token = decrypt_api_key(encrypted_token)
                    logger.info(f"Using decrypted GitLab token from organization {organization.title}")
                except Exception as e:
                    logger.error(f"Failed to decrypt GitLab token for organization {organization.title}: {str(e)}")
                    gitlab_token = None
        
        if not gitlab_token:
            logger.warning(f"No GitLab token found in organization {organization.title} properties")
        
        # Use temp directory for repository work
        with tempfile.TemporaryDirectory() as temp_dir:
            template_repo_path = os.path.join(temp_dir, "student-template")
            
            # Create authenticated URL if we have a token and it's HTTP
            auth_url = student_template_url
            if gitlab_token and 'http' in student_template_url:
                from urllib.parse import urlparse, urlunparse
                parsed = urlparse(student_template_url)
                auth_netloc = f"oauth2:{gitlab_token}@{parsed.hostname}"
                if parsed.port:
                    auth_netloc += f":{parsed.port}"
                auth_url = urlunparse((
                    parsed.scheme,
                    auth_netloc,
                    parsed.path,
                    parsed.params,
                    parsed.query,
                    parsed.fragment
                ))
            
            # Try to clone existing repo or create new one
            try:
                if gitlab_token and 'http' in student_template_url:
                    template_repo = git.Repo.clone_from(auth_url, template_repo_path)
                else:
                    template_repo = git.Repo.clone_from(student_template_url, template_repo_path)
            except Exception as e:
                logger.info(f"Could not clone student template repo, creating new: {e}")
                os.makedirs(template_repo_path, exist_ok=True)
                template_repo = git.Repo.init(template_repo_path)
                
                # Set default branch to main
                template_repo.git.checkout('-b', 'main')
                
                # Add remote with auth URL if we have a token
                if 'http' in student_template_url:
                    if gitlab_token:
                        template_repo.create_remote('origin', auth_url)
                    else:
                        template_repo.create_remote('origin', student_template_url)
            
            # Configure git for commits (required in worker container)
            git_email = os.environ.get('SYSTEM_GIT_EMAIL', 'worker@computor.local')
            git_name = os.environ.get('SYSTEM_GIT_NAME', 'Computor Worker')
            template_repo.git.config('user.email', git_email)
            template_repo.git.config('user.name', git_name)
            
            # Clone assignments repository for reading released content
            # Derive assignments_url if not provided
            if not assignments_url:
                course_props = course.properties or {}
                course_gitlab = course_props.get('gitlab', {})
                provider = (organization.properties or {}).get('gitlab', {}).get('url')
                full_path_course = course_gitlab.get('full_path')
                if provider and full_path_course:
                    assignments_url = f"{provider}/{full_path_course}/assignments.git"
            if not assignments_url:
                raise ValueError("assignments_url is required or must be derivable from course properties")

            # Transform localhost URL for Docker environment
            assignments_url = transform_localhost_url(assignments_url)

            # Prepare local path for assignments repo and authenticated URL
            assignments_repo_path = os.path.join(temp_dir, 'assignments')
            assignments_auth_url = assignments_url
            if gitlab_token and 'http' in assignments_url:
                from urllib.parse import urlparse, urlunparse
                parsed = urlparse(assignments_url)
                auth_netloc = f"oauth2:{gitlab_token}@{parsed.hostname}"
                if parsed.port:
                    auth_netloc += f":{parsed.port}"
                assignments_auth_url = urlunparse((parsed.scheme, auth_netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))

            try:
                if gitlab_token and 'http' in assignments_url:
                    assignments_repo = git.Repo.clone_from(assignments_auth_url, assignments_repo_path)
                else:
                    assignments_repo = git.Repo.clone_from(assignments_url, assignments_repo_path)
            except Exception as e:
                logger.error(f"Failed to clone assignments repository: {e}")
                # Mark all selected deployments as failed and record history
                for deployment in deployments_to_process:
                    if deployment.deployment_status == "deploying":
                        deployment.deployment_status = "failed"
                        deployment.deployment_message = f"Failed to clone assignments: {str(e)[:200]}"
                        history = DeploymentHistory(
                            deployment_id=deployment.id,
                            action="failed",
                            example_version_id=deployment.example_version_id,
                            workflow_id=workflow_id,
                        )
                        db.add(history)
                db.commit()
                return {"success": False, "error": f"Failed to clone assignments: {str(e)}"}

            # Do not clean the whole repository; only update selected directories
            
            # Determine course contents to deploy (selected or by status)
            if selected_course_content_ids:
                course_contents = db.query(CourseContent).options(
                    joinedload(CourseContent.deployment)
                        .joinedload(CourseContentDeployment.example_version)
                        .joinedload(ExampleVersion.example)
                ).filter(
                    CourseContent.id.in_(selected_course_content_ids),
                    CourseContent.archived_at.is_(None)
                ).order_by(CourseContent.path).all()
            else:
                course_contents = db.query(CourseContent).options(
                    joinedload(CourseContent.deployment)
                        .joinedload(CourseContentDeployment.example_version)
                        .joinedload(ExampleVersion.example)
                ).filter(
                    CourseContent.course_id == course_id,
                    CourseContent.archived_at.is_(None)
                ).order_by(CourseContent.path).all()
            
            logger.info(f"Selected {len(course_contents)} course contents to deploy")
            
            if len(course_contents) == 0:
                logger.warning(f"No course contents to deploy for course {course_id}. This will result in an empty student template.")
            
            # Process each CourseContent with an example
            processed_count = 0
            errors = []
            successfully_processed = []  # Track which content was successfully processed
            
            for content in course_contents:
                try:
                    if not content.deployment:
                        # Skip non-assigned items (e.g., container units)
                        logger.info(f"Skipping {content.path}: no deployment assigned")
                        continue

                    # Validate deployment_path is set (should be set during assignment)
                    if not content.deployment.deployment_path:
                        error_msg = f"deployment_path not set for {content.path} - this should be set during assignment"
                        logger.error(error_msg)
                        errors.append(error_msg)

                        # Mark deployment as failed
                        if content.deployment.deployment_status == "deploying":
                            content.deployment.deployment_status = "failed"
                            content.deployment.deployment_message = "deployment_path not set"
                            history = DeploymentHistory(
                                deployment_id=content.deployment.id,
                                action="failed",
                                example_version_id=content.deployment.example_version_id,
                                workflow_id=workflow_id,
                            )
                            db.add(history)
                        continue

                    # Resolve commit to use for this content
                    overrides_list = []
                    if release:
                        try:
                            raw_ovr = release.get('overrides')
                            if isinstance(raw_ovr, list):
                                overrides_list = raw_ovr
                        except Exception:
                            overrides_list = []
                    commit_override_map = {}
                    for ov in overrides_list:
                        if not ov:
                            continue
                        cid = ov.get('course_content_id')
                        vid = ov.get('version_identifier')
                        if cid and vid:
                            commit_override_map[str(cid)] = vid
                    desired_commit = commit_override_map.get(str(content.id)) if release else None
                    global_commit = release.get('global_commit') if release else None
                    try:
                        if desired_commit:
                            commit_to_use = str(assignments_repo.commit(desired_commit).hexsha)
                        elif global_commit:
                            commit_to_use = str(assignments_repo.commit(global_commit).hexsha)
                        else:
                            commit_to_use = content.deployment.version_identifier
                    except Exception as e:
                        logger.warning(f"Failed to resolve commit for {content.path}: {e}")
                        commit_to_use = None

                    # Extract execution backend slug from meta.yaml (if needed) and link to course_content
                    if not content.execution_backend_id:
                        try:
                            commit_obj = assignments_repo.commit(commit_to_use)
                            meta_blob = commit_obj.tree / content.deployment.deployment_path / 'meta.yaml'
                            meta_yaml_bytes = meta_blob.data_stream.read()
                            import yaml
                            meta_data = yaml.safe_load(meta_yaml_bytes) if meta_yaml_bytes else None
                            backend_slug = None
                            if meta_data:
                                props = (meta_data.get('properties') or {})
                                eb = props.get('executionBackend') or {}
                                backend_slug = eb.get('slug')
                            if backend_slug:
                                exec_backend = db.query(ExecutionBackend).filter(ExecutionBackend.slug == backend_slug).first()
                                if exec_backend:
                                    content.execution_backend_id = exec_backend.id
                                    logger.info(f"Linked execution backend '{backend_slug}' to course content {content.path}")
                        except Exception:
                            pass

                    # Build files map from assignments repo at the selected commit under deployment path
                    files: Dict[str, bytes] = {}
                    if commit_to_use:
                        try:
                            commit_obj = assignments_repo.commit(commit_to_use)
                            sub_tree = commit_obj.tree / content.deployment.deployment_path
                            for item in sub_tree.traverse():
                                if item.type == 'blob':
                                    rel_path = os.path.relpath(item.path, content.deployment.deployment_path)
                                    files[rel_path] = item.data_stream.read()
                        except Exception as e:
                            logger.warning(f"Failed to load files from assignments for {content.path}: {e}")
                            files = {}
                    
                    if not files:
                        # Strict mode: fail when assignments does not provide files
                        reason = "no files in assignments at commit" if commit_to_use else "no commit resolved"
                        logger.error(f"Release failed for {content.path}: {reason}")
                        content.deployment.deployment_status = "failed"
                        content.deployment.deployment_message = f"Assignments {reason}"
                        history = DeploymentHistory(
                            deployment_id=content.deployment.id,
                            action="failed",
                            example_version_id=content.deployment.example_version_id,
                            workflow_id=workflow_id,
                        )
                        db.add(history)
                        errors.append(f"{str(content.path)}: {reason}")
                        continue
                    
                    logger.info(f"Downloaded {len(files)} files for {content.path}")
                    
                    # Determine target directory in student template
                    # Use the example identifier as directory name for better organization
                    target_dir = str(content.deployment.deployment_path)
                    full_target_path = os.path.join(template_repo_path, target_dir)
                    
                    # Process the example files for student template
                    # This function handles meta.yaml properties like studentSubmissionFiles,
                    # studentTemplates, additionalFiles, and content directory processing
                    process_result = await process_example_for_student_template_v2(
                        example_files=files,
                        target_path=Path(full_target_path),
                        course_content=content,
                        version=None
                    )
                    
                    if not process_result.get("success"):
                        error_msg = process_result.get("error", "Unknown error during processing")
                        logger.error(f"Failed to process example for {content.path}: {error_msg}")
                        errors.append(f"Processing failed for {content.path}: {error_msg}")
                        continue
                    
                    processed_count += 1
                    logger.info(f"Successfully processed {content.path}")
                    
                    # Update deployment version to the commit used for this content (only if from assignments)
                    if commit_to_use:
                        content.deployment.version_identifier = commit_to_use
                    # Track that we processed it successfully
                    successfully_processed.append(content)
                    
                except Exception as e:
                    error_msg = f"Failed to process {content.path}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    errors.append(error_msg)
                    
                    # Update deployment status to failed with history
                    if content.deployment:
                        content.deployment.deployment_status = "failed"
                        content.deployment.deployment_message = str(e)[:500]  # Truncate error message
                        
                        # Add failure history entry
                        history = DeploymentHistory(
                            deployment_id=content.deployment.id,
                            action="failed",
                            example_version_id=content.deployment.example_version_id,
                            workflow_id=workflow_id,
                        )
                        db.add(history)
            
            # Don't commit yet - wait until after git operations
            
            # Generate main README.md with assignment structure
            # IMPORTANT: Show ALL deployed assignments in the repository, not just newly released ones
            if processed_count > 0 or True:  # Always generate README, even if no new assignments
                main_readme_path = os.path.join(template_repo_path, "README.md")

                # Fetch ALL course contents with DEPLOYED status to show current repository state
                all_deployed_contents = db.query(CourseContent).options(
                    joinedload(CourseContent.deployment)
                        .joinedload(CourseContentDeployment.example_version)
                        .joinedload(ExampleVersion.example)
                ).filter(
                    CourseContent.course_id == course_id,
                    CourseContent.archived_at.is_(None),
                    CourseContent.deployment.has(CourseContentDeployment.deployment_status == 'deployed')
                ).order_by(CourseContent.path).all()

                logger.info(f"Found {len(all_deployed_contents)} deployed assignments for README generation")

                with open(main_readme_path, 'w') as f:
                    f.write(f"# {course.title} - Student Template\n\n")
                    f.write(f"This repository contains {len(all_deployed_contents)} assignments for {course.title}.\n\n")

                    # Generate assignment structure table
                    if all_deployed_contents:
                        f.write(f"## Assignment Structure\n\n")
                        f.write(f"| Content Path | Assignment Directory | Title | Version |\n")
                        f.write(f"|-------------|---------------------|-------|----------|\n")

                        # Fetch all course contents to build complete path hierarchy
                        all_contents = db.query(CourseContent).filter(
                            CourseContent.course_id == course_id,
                            CourseContent.archived_at.is_(None)
                        ).all()

                        # Build a complete map of paths to titles
                        path_to_title = {}
                        for content in all_contents:
                            path_to_title[str(content.path)] = content.title

                        for content in all_deployed_contents:
                            if content.deployment and content.deployment.example_version:
                                example = content.deployment.example_version.example
                                version = content.deployment.example_version.version_tag

                                # Build title path with "/" separation
                                path_parts = str(content.path).split('.')
                                title_parts = []

                                # Build up the path progressively to find each part's title
                                for i, part in enumerate(path_parts):
                                    # Reconstruct path up to this part
                                    current_path = '.'.join(path_parts[:i+1])

                                    # Try to find title for this path segment
                                    if current_path in path_to_title:
                                        title_parts.append(path_to_title[current_path])
                                    else:
                                        # If we can't find the title, use the path segment as fallback
                                        title_parts.append(part)

                                # Join with " / " as requested
                                title_path = " / ".join(title_parts)

                                f.write(f"| {title_path} | `{example.identifier}/` | {content.title} | {version} |\n")
                    else:
                        f.write(f"*No assignments deployed yet.*\n\n")

                    f.write(f"\n## Instructions\n\n")
                    f.write(f"Each assignment is in its own directory. Navigate to the assignment directory and follow the instructions in its README.md file.\n\n")
                    f.write(f"## Submission\n\n")
                    f.write(f"Follow your course submission guidelines for each assignment.\n\n")
                    f.write(f"---\n")
                    f.write(f"*Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}*\n")
                    f.write(f"*Generated by Computor Example Library*\n")

                logger.info(f"Generated main README.md with {len(all_deployed_contents)} deployed assignments (current state)")
            
            # If we processed any content, commit and push to Git
            git_push_successful = False
            if processed_count > 0:
                try:
                    # Stage all changes
                    template_repo.git.add(A=True)
                    
                    # Check if there are changes to commit
                    if template_repo.is_dirty() or template_repo.untracked_files:
                        # Commit changes - selective release
                        commit_message = f"Release {processed_count} assignments to student template"
                        template_repo.index.commit(commit_message)
                        logger.info(f"Committed changes: {commit_message}")
                        
                        # Push to remote
                        if 'origin' in [remote.name for remote in template_repo.remotes]:
                            # The remote should already have auth URL if token was provided
                            # Just push directly
                            template_repo.git.push('origin', 'main')
                            logger.info("Pushed changes to GitLab")
                            git_push_successful = True
                        else:
                            logger.warning("No remote 'origin' found, skipping push")
                            git_push_successful = True  # Consider successful if no remote
                    else:
                        logger.info("No changes to commit")
                        git_push_successful = True  # No changes needed
                        
                except Exception as e:
                    error_msg = f"Failed to commit/push changes: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    git_push_successful = False
            
            # Now update deployment statuses based on git push result
            # Only update deployments that were marked as "deploying" at the start
            if git_push_successful and processed_count > 0:
                # Mark successfully processed content as deployed (only if currently deploying)
                for content in successfully_processed:
                    if content.deployment and content.deployment.deployment_status == "deploying":
                        content.deployment.deployment_status = "deployed"
                        content.deployment.deployed_at = datetime.now(timezone.utc)
                        
                        # Add success history entry
                        history = DeploymentHistory(
                            deployment_id=content.deployment.id,
                            action="deployed",
                            example_version_id=content.deployment.example_version_id,
                            workflow_id=workflow_id,
                        )
                        db.add(history)
            else:
                # Git push failed - mark only the ones we're processing as failed
                for content in course_contents:
                    if content.deployment and content.deployment.deployment_status == "deploying":
                        content.deployment.deployment_status = "failed"
                        content.deployment.deployment_message = "Git push failed"
                        
                        # Add failure history entry
                        history = DeploymentHistory(
                            deployment_id=content.deployment.id,
                            action="failed",
                            example_version_id=content.deployment.example_version_id,
                            workflow_id=workflow_id,
                        )
                        db.add(history)
            
            # Now commit database changes
            db.commit()
            
            # Do not generate assignments repository automatically; managed manually by lecturers
            assignments_result = None
            
            # Prepare result
            success = processed_count > 0 and len(errors) < len(course_contents)
            
            result = {
                "success": success,
                "processed_count": processed_count,
                "total_count": len(course_contents),
                "errors": errors,
                "message": f"Processed {processed_count}/{len(course_contents)} examples"
            }
            
            if errors:
                result["message"] += f" with {len(errors)} errors"
            
            if assignments_result:
                result["assignments"] = assignments_result
            
            return result
            
    except Exception as e:
        logger.error(f"Failed to generate student template: {str(e)}", exc_info=True)
        
        # Mark all 'deploying' deployments as failed
        try:
            failed_deployments = db.query(CourseContentDeployment).join(
                CourseContent
            ).filter(
                and_(
                    CourseContent.course_id == course_id,
                    CourseContentDeployment.deployment_status == "deploying"
                )
            ).all()
            
            for deployment in failed_deployments:
                deployment.deployment_status = "failed"
                deployment.deployment_message = str(e)[:500]
                
                # Add failure history
                history = DeploymentHistory(
                    deployment_id=deployment.id,
                    action="failed",
                    example_version_id=deployment.example_version_id,
                    workflow_id=workflow_id,
                )
                db.add(history)
            
            db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update deployment statuses: {db_error}")
        
        return {
            "success": False,
            "processed_count": 0,
            "errors": [str(e)],
            "message": f"Failed to generate student template: {str(e)}"
        }
    finally:
        db_gen.close()


@register_task
@workflow.defn(name="generate_student_template_v2", sandboxed=False)
class GenerateStudentTemplateWorkflowV2(BaseWorkflow):
    """
    Temporal workflow for generating student template repositories.
    
    This workflow orchestrates the generation of student templates from
    examples stored in the Example Library.
    """
    
    @classmethod
    def get_name(cls) -> str:
        """Get the workflow name for registration."""
        return "generate_student_template_v2"

    @classmethod
    def get_task_queue(cls) -> str:
        return "computor-tasks"
    
    @classmethod
    def get_execution_timeout(cls) -> timedelta:
        return timedelta(minutes=30)
    
    @workflow.run
    async def run(self, params: Dict[str, Any]) -> WorkflowResult:
        """Run the student template generation workflow."""
        course_id = params.get('course_id')
        student_template_url = params.get('student_template_url')
        assignments_url = params.get('assignments_url')  # Get assignments URL
        force_redeploy = params.get('force_redeploy', False)  # Default to False if not provided
        
        if not course_id:
            return WorkflowResult(
                status="failed",
                result=None,
                error="course_id is required"
            )
        
        if not student_template_url:
            return WorkflowResult(
                status="failed",
                result=None,
                error="student_template_url is required"
            )
        
        # Get workflow ID for tracking
        workflow_id = workflow.info().workflow_id
        
        # Execute the activity with retry policy
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=5),
            maximum_interval=timedelta(minutes=1),
            maximum_attempts=3,
            backoff_coefficient=2.0
        )
        
        try:
            # Build release selection/options from params
            release = params.get('release') or {
                'course_content_ids': params.get('course_content_ids'),
                'parent_id': params.get('parent_id'),
                'include_descendants': params.get('include_descendants'),
                'all': params.get('all'),
                'global_commit': params.get('global_commit'),
                'overrides': params.get('overrides'),
            }

            result = await workflow.execute_activity(
                generate_student_template_activity_v2,
                args=[course_id, student_template_url, assignments_url, workflow_id, force_redeploy, release],
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=retry_policy
            )
            
            return WorkflowResult(
                status="completed" if result.get('success', False) else "failed",
                result=result,
                error=result.get('errors', []) if not result.get('success') else None,
                metadata={"workflow_id": workflow_id}
            )
            
        except Exception as e:
            logger.error(f"Workflow failed: {str(e)}")
            return WorkflowResult(
                status="failed",
                result=None,
                error=str(e)
            )
