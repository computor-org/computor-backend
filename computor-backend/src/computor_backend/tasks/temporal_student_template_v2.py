"""
Temporal workflows for generating student templates from Example Library.
Version 2: Fixed deployment status handling and sandbox restrictions.
"""
import logging
from datetime import timedelta
from typing import Dict, Any, List

from temporalio import workflow, activity
from temporalio.common import RetryPolicy

from .temporal_base import BaseWorkflow, WorkflowResult, decrypt_gitlab_token, make_git_auth_url
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
    File lists come from the ExampleVersion DB row (typed columns), not
    from re-parsing the workspace meta.yaml.
    """
    from pathlib import Path

    try:
        # Create target directory
        target_path.mkdir(parents=True, exist_ok=True)

        # File lists from typed columns on ExampleVersion. These were
        # derived from meta.yaml at upload and are the source of truth
        # for what files belong to this version.
        additional_files = list(getattr(version, 'additional_files', None) or [])
        submission_files = list(getattr(version, 'student_submission_files', None) or [])
        student_templates = list(getattr(version, 'student_templates', None) or [])
        has_meta = (
            additional_files or submission_files or student_templates
            or getattr(version, 'meta', None)
        )

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

        if has_meta:
            # Process additionalFiles - copy to assignment root
            for file_name in additional_files:
                if file_name in example_files:
                    # Copy to root of assignment directory
                    file_path = target_path / Path(file_name).name  # Use only filename, not path
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_bytes(example_files[file_name])
            
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
    # Extract bucket name from source_url (format: "bucket-name" or "bucket-name/prefix")
    bucket_name = repository.source_url.split('/')[0]
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
    from ..database import get_db_session
    from ..model.course import Course, CourseContent
    from ..model.example import Example, ExampleVersion, ExampleRepository
    from ..model.deployment import CourseContentDeployment, DeploymentHistory
    from ..model.service import ServiceType
    from ..services.storage_service import StorageService

    with get_db_session() as db:
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
            selected_course_content_ids = release.get("course_content_ids") or []

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
        # Capture previous statuses for broadcast
        deploying_events = []
        for deployment in deployments_to_process:
            # Track previous status for broadcast
            previous_status = deployment.deployment_status

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

            deploying_events.append({
                "deployment_id": str(deployment.id),
                "course_content_id": str(deployment.course_content_id),
                "previous_status": previous_status,
                "version_tag": deployment.version_tag,
                "example_identifier": str(deployment.example_identifier) if deployment.example_identifier else None,
            })

        db.commit()

        # Broadcast deployment status changes after successful commit
        from computor_backend.websocket.event_publisher import publish_deployment_status_changed
        for evt in deploying_events:
            publish_deployment_status_changed(
                course_id=str(course_id),
                course_content_id=evt["course_content_id"],
                deployment_id=evt["deployment_id"],
                previous_status=evt["previous_status"],
                new_status="deploying",
                version_tag=evt["version_tag"],
                example_identifier=evt["example_identifier"],
                workflow_id=workflow_id,
            )

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
            gitlab_token = decrypt_gitlab_token(gitlab_config.get('token'))
            if gitlab_token:
                logger.info(f"Using decrypted GitLab token from organization {organization.title}")
        
        if not gitlab_token:
            logger.warning(f"No GitLab token found in organization {organization.title} properties")
        
        # Use temp directory for repository work
        with tempfile.TemporaryDirectory() as temp_dir:
            template_repo_path = os.path.join(temp_dir, "student-template")
            
            # Create authenticated URL if we have a token and it's HTTP
            auth_url = make_git_auth_url(student_template_url, gitlab_token) if gitlab_token else student_template_url
            
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

            # NOTE: We do NOT use the assignments repository here!
            # All example content comes directly from MinIO via download_example_files()
            # The assignments repository is managed separately by temporal_assignments_repository.py

            # REPOSITORY STATE VERIFICATION
            # Scan what's actually present in the cloned repository to detect state mismatches
            existing_directories = set()
            current_repo_sha = None

            try:
                for item in os.listdir(template_repo_path):
                    item_path = os.path.join(template_repo_path, item)
                    if os.path.isdir(item_path) and item != '.git':
                        existing_directories.add(item)

                # Get current repository HEAD commit SHA if it exists
                if template_repo.head.is_valid():
                    current_repo_sha = template_repo.head.commit.hexsha
                    logger.info(f"Repository scan: Found {len(existing_directories)} existing directories, HEAD={current_repo_sha[:8]}")
                else:
                    logger.info(f"Repository scan: Found {len(existing_directories)} existing directories (no commits yet)")
            except Exception as e:
                logger.warning(f"Failed to scan repository state: {e}. Proceeding without verification.")

            # Query ALL course contents that have deployments (not just those being deployed)
            # This allows us to detect state mismatches where DB says "deployed" but repo is missing content
            all_course_contents = db.query(CourseContent).options(
                joinedload(CourseContent.deployment)
                    .joinedload(CourseContentDeployment.example_version)
                    .joinedload(ExampleVersion.example)
            ).filter(
                CourseContent.course_id == course_id,
                CourseContent.archived_at.is_(None),
                CourseContent.deployment.has()  # Has a deployment record
            ).order_by(CourseContent.path).all()

            logger.info(f"Found {len(all_course_contents)} course contents with deployments")

            # Determine which contents need to be processed
            course_contents = []
            state_mismatches = 0

            for content in all_course_contents:
                # Get deployment path using same fallback logic as processing loop
                deployment_path = content.deployment.deployment_path
                if not deployment_path and content.deployment.example_identifier:
                    deployment_path = str(content.deployment.example_identifier)
                if not deployment_path and content.deployment.example_version:
                    try:
                        example = content.deployment.example_version.example
                        if example and example.identifier:
                            deployment_path = str(example.identifier)
                    except AttributeError:
                        # Lazy-loaded relationship missing under detached session — skip,
                        # caller will fall through to the empty-deployment branch.
                        pass

                exists_in_repo = deployment_path in existing_directories if deployment_path else False

                # Determine if this content needs processing
                should_process = False
                reason = None

                # If specific contents were selected, only process those
                if selected_course_content_ids:
                    if str(content.id) in selected_course_content_ids:
                        should_process = True
                        reason = "selected for deployment"
                else:
                    # Check various conditions for processing
                    if content.deployment.deployment_status in ["pending", "failed", "deploying"]:
                        should_process = True
                        reason = f"status={content.deployment.deployment_status}"
                    elif force_redeploy:
                        should_process = True
                        reason = "force_redeploy=True"
                    elif content.deployment.deployment_status == "deployed" and not exists_in_repo:
                        # STATE MISMATCH: DB says deployed but missing from repository
                        should_process = True
                        reason = "STATE MISMATCH: marked deployed but missing from repository"
                        state_mismatches += 1
                        logger.warning(
                            f"🔄 STATE MISMATCH DETECTED: {content.path} ({deployment_path}) "
                            f"is marked as 'deployed' in database but MISSING from repository. "
                            f"Will re-deploy to fix inconsistency."
                        )
                        # Mark for reprocessing
                        content.deployment.deployment_status = "deploying"
                        content.deployment.deployment_message = "Re-deploying due to repository state mismatch"

                if should_process:
                    course_contents.append(content)
                    logger.info(f"  → Will process {content.path}: {reason}")

            if state_mismatches > 0:
                logger.warning(
                    f"⚠️  Detected {state_mismatches} state mismatch(es) between database and repository. "
                    f"These will be automatically fixed by re-deploying the missing content."
                )

            logger.info(f"Selected {len(course_contents)} course contents to process")
            
            if not course_contents:
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

                    # Get deployment path - use deployment_path if set, otherwise fall back to example_identifier
                    directory_name = content.deployment.deployment_path
                    if not directory_name:
                        if content.deployment.example_identifier:
                            # Use example_identifier as-is for the directory name
                            directory_name = str(content.deployment.example_identifier)
                            # Save it to deployment_path so it's persisted in the database
                            content.deployment.deployment_path = directory_name
                            logger.info(f"Auto-set deployment_path from example_identifier for {content.path}: {directory_name}")
                        elif content.deployment.example_version:
                            # Try to get identifier from the example_version relationship
                            try:
                                example = content.deployment.example_version.example
                                if example and example.identifier:
                                    directory_name = str(example.identifier)
                                    content.deployment.deployment_path = directory_name
                                    logger.info(f"Auto-set deployment_path from example.identifier for {content.path}: {directory_name}")
                            except Exception as e:
                                logger.warning(f"Could not get identifier from example_version: {e}")

                        # If still no directory_name, this is a critical error
                        if not directory_name:
                            error_msg = (
                                f"❌ CRITICAL: Cannot deploy {content.path} - no deployment_path, no example_identifier, "
                                f"and no example.identifier available. This CourseContentDeployment record is invalid. "
                                f"Deployment ID: {content.deployment.id}"
                            )
                            logger.error(error_msg)
                            errors.append(error_msg)

                            # Mark deployment as failed with detailed message
                            if content.deployment.deployment_status == "deploying":
                                content.deployment.deployment_status = "failed"
                                content.deployment.deployment_message = (
                                    "Cannot determine deployment directory: deployment_path, example_identifier, "
                                    "and example.identifier are all NULL"
                                )
                                history = DeploymentHistory(
                                    deployment_id=content.deployment.id,
                                    action="failed",
                                    example_version_id=content.deployment.example_version_id,
                                    workflow_id=workflow_id,
                                )
                                db.add(history)
                            continue

                    # Download files from example repository (MinIO or Git based on source_type)
                    # NOTE: We download directly from MinIO/ExampleRepository, NOT from assignments repo!
                    files: Dict[str, bytes] = {}
                    try:
                        if content.deployment.example_version:
                            example_repo = content.deployment.example_version.example.repository
                            # download_example_files returns files already scoped to the example version
                            # No filtering needed - the storage_path in MinIO already isolates this example
                            files = await download_example_files(example_repo, content.deployment.example_version)
                    except Exception as e:
                        logger.warning(f"Failed to load files from example repository for {content.path}: {e}")
                        files = {}

                    # Legacy fallback: link a testing service by language when
                    # the slug→service.id resolution didn't fire. Reads from
                    # the ExampleVersion's typed ``execution_backend`` column
                    # first; falls back to parsing the meta.yaml that's
                    # already in the ``files`` dict for the rare
                    # ``properties.serviceType`` path.
                    if not content.testing_service_id and content.deployment.example_version:
                        try:
                            ev = content.deployment.example_version
                            language = None

                            # New ``properties.serviceType`` path lives only
                            # in meta.yaml — parse the workspace copy if we
                            # have it.
                            meta_yaml_bytes = files.get('meta.yaml') if files else None
                            if meta_yaml_bytes:
                                import yaml as _yaml
                                try:
                                    meta_data = _yaml.safe_load(meta_yaml_bytes) or {}
                                except Exception:
                                    meta_data = {}
                                props = meta_data.get('properties') if isinstance(meta_data.get('properties'), dict) else {}
                                service_type_spec = props.get('serviceType') or props.get('service_type')
                                if service_type_spec and isinstance(service_type_spec, str) and service_type_spec.startswith('testing.'):
                                    # e.g., "testing.python" -> "python"
                                    language = service_type_spec.split('.')[-1]

                            if not language:
                                # Legacy: map executionBackend.slug suffix to language
                                backend_slug = (ev.execution_backend or {}).get('slug') if isinstance(ev.execution_backend, dict) else None
                                if backend_slug:
                                    slug_parts = backend_slug.split('.')
                                    backend_type = slug_parts[-1] if slug_parts else backend_slug
                                    legacy_mapping = {
                                        'py': 'python',
                                        'python': 'python',
                                        'matlab': 'matlab',
                                        'mat': 'matlab',
                                    }
                                    language = legacy_mapping.get(backend_type)

                            if language:
                                from sqlalchemy_utils import Ltree
                                from ..model.service import Service

                                # Find the testing.temporal ServiceType
                                service_type = db.query(ServiceType).filter(
                                    ServiceType.path == Ltree('testing.temporal')
                                ).first()

                                if service_type:
                                    # Find a Service with this service_type_id AND matching language
                                    # Prefer enabled services
                                    service = db.query(Service).filter(
                                        Service.service_type_id == service_type.id,
                                        Service.enabled == True,
                                        Service.properties['language'].astext == language
                                    ).first()

                                    if service:
                                        content.testing_service_id = service.id
                                        logger.info(f"Linked service '{service.slug}' (language: {language}) to course content {content.path}")
                                    else:
                                        logger.warning(f"No enabled Service found for language '{language}' with ServiceType 'testing.temporal'")
                                else:
                                    logger.warning(f"ServiceType 'testing.temporal' not found - run seed_testing_temporal_service_type.py")
                        except Exception as e:
                            logger.warning(f"Failed to link service: {e}")

                    if not files:
                        # Strict mode: fail when example repository does not provide files
                        reason = "no files in example repository" if content.deployment.example_version else "no example version configured"
                        logger.error(f"Release failed for {content.path}: {reason}")
                        content.deployment.deployment_status = "failed"
                        content.deployment.deployment_message = f"Example repository: {reason}"
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
                    target_dir = str(directory_name)
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

            # Fetch ALL course contents that are deployed OR being deployed in this run
            # We include "deploying" status because README is generated BEFORE status update
            all_deployed_contents = db.query(CourseContent).options(
                    joinedload(CourseContent.deployment)
                        .joinedload(CourseContentDeployment.example_version)
                        .joinedload(ExampleVersion.example)
                ).filter(
                CourseContent.course_id == course_id,
                CourseContent.archived_at.is_(None),
                CourseContent.deployment.has(
                    CourseContentDeployment.deployment_status.in_(['deployed', 'deploying'])
                )
            ).order_by(CourseContent.path).all()

            logger.info(f"Found {len(all_deployed_contents)} deployed/deploying assignments for README generation")

            # Always generate README to reflect current state
            main_readme_path = os.path.join(template_repo_path, "README.md")
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

                            # Create clickable link to the directory
                            directory_link = f"[`{example.identifier}/`](./{example.identifier})"

                            f.write(f"| {title_path} | {directory_link} | {content.title} | {version} |\n")
                else:
                    f.write(f"*No assignments deployed yet.*\n\n")

                f.write(f"\n## Instructions\n\n")
                f.write(f"Each assignment is in its own directory. Navigate to the assignment directory and follow the instructions in its README.md file.\n\n")
                f.write(f"## Submission\n\n")
                f.write(f"Follow your course submission guidelines for each assignment.\n\n")
                f.write(f"---\n")
                f.write(f"*Generated by Computor*\n")

            logger.info(f"Generated main README.md with {len(all_deployed_contents)} deployed assignments (current state)")

            # Commit and push to Git if we processed content OR if README changed
            # This ensures README is always up-to-date even if no new deployments occurred
            git_push_successful = False
            if processed_count > 0 or (len(all_deployed_contents) > 0 and os.path.exists(os.path.join(template_repo_path, "README.md"))):
                try:
                    # Stage all changes
                    template_repo.git.add(A=True)
                    
                    # Check if there are changes to commit
                    if template_repo.is_dirty() or template_repo.untracked_files:
                        # Commit changes with simple message
                        commit_message = "System Release"
                        template_repo.index.commit(commit_message)
                        logger.info(f"Committed changes: {commit_message}")
                        
                        # Push to remote with retry on concurrent push conflicts
                        if 'origin' in [remote.name for remote in template_repo.remotes]:
                            max_push_attempts = 3
                            for push_attempt in range(max_push_attempts):
                                try:
                                    template_repo.git.push('origin', 'main')
                                    logger.info("Pushed changes to GitLab")
                                    git_push_successful = True
                                    break
                                except git.GitCommandError as push_err:
                                    err_msg = str(push_err).lower()
                                    if 'non-fast-forward' in err_msg or 'fetch first' in err_msg or 'failed to push' in err_msg:
                                        if push_attempt < max_push_attempts - 1:
                                            logger.warning(
                                                f"Push failed (attempt {push_attempt + 1}/{max_push_attempts}), "
                                                f"pulling with rebase and retrying: {push_err}"
                                            )
                                            template_repo.git.pull('--rebase', 'origin', 'main')
                                        else:
                                            logger.error(f"Push failed after {max_push_attempts} attempts: {push_err}")
                                            raise
                                    else:
                                        raise
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
            # Collect status changes for broadcast after commit
            final_status_events = []

            if git_push_successful and processed_count > 0:
                # Get the final commit SHA from student-template repository
                try:
                    final_template_sha = template_repo.head.commit.hexsha
                    logger.info(f"Student-template repository now at commit: {final_template_sha[:8]}")
                except Exception as e:
                    logger.warning(f"Could not get repository commit SHA: {e}")
                    final_template_sha = None

                # Mark successfully processed content as deployed (only if currently deploying)
                for content in successfully_processed:
                    if content.deployment and content.deployment.deployment_status == "deploying":
                        content.deployment.deployment_status = "deployed"
                        content.deployment.deployed_at = datetime.now(timezone.utc)
                        content.deployment.deployment_message = None  # Clear any error messages

                        # Store the student-template git commit SHA for audit trail
                        # This allows tracking exactly which commit contains this deployment
                        if final_template_sha:
                            content.deployment.version_identifier = final_template_sha

                        # Ensure version_tag is populated from example_version (if not already set)
                        # This tracks which example version (from MinIO) was deployed
                        if not content.deployment.version_tag and content.deployment.example_version:
                            try:
                                content.deployment.version_tag = content.deployment.example_version.version_tag
                                logger.info(f"Set version_tag={content.deployment.version_tag} for {content.path}")
                            except Exception as e:
                                logger.warning(f"Could not set version_tag for {content.path}: {e}")

                        # Add success history entry
                        history = DeploymentHistory(
                            deployment_id=content.deployment.id,
                            action="deployed",
                            example_version_id=content.deployment.example_version_id,
                            workflow_id=workflow_id,
                        )
                        db.add(history)

                        final_status_events.append({
                            "course_content_id": str(content.id),
                            "deployment_id": str(content.deployment.id),
                            "new_status": "deployed",
                            "version_tag": content.deployment.version_tag,
                            "example_identifier": str(content.deployment.example_identifier) if content.deployment.example_identifier else None,
                            "deployed_at": content.deployment.deployed_at.isoformat() if content.deployment.deployed_at else None,
                        })
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

                        final_status_events.append({
                            "course_content_id": str(content.id),
                            "deployment_id": str(content.deployment.id),
                            "new_status": "failed",
                            "deployment_message": "Git push failed",
                            "version_tag": content.deployment.version_tag,
                            "example_identifier": str(content.deployment.example_identifier) if content.deployment.example_identifier else None,
                        })

            # Also collect any content that was marked as failed during processing
            # (directory resolution, file download, processing exceptions)
            for content in course_contents:
                if content.deployment and content.deployment.deployment_status == "failed":
                    # Check if already in final_status_events to avoid duplicates
                    already_tracked = any(
                        e["deployment_id"] == str(content.deployment.id)
                        for e in final_status_events
                    )
                    if not already_tracked:
                        final_status_events.append({
                            "course_content_id": str(content.id),
                            "deployment_id": str(content.deployment.id),
                            "new_status": "failed",
                            "deployment_message": content.deployment.deployment_message,
                            "version_tag": content.deployment.version_tag,
                            "example_identifier": str(content.deployment.example_identifier) if content.deployment.example_identifier else None,
                        })

            # Now commit database changes
            db.commit()

            # Broadcast all status changes after successful commit
            from computor_backend.websocket.event_publisher import publish_deployment_status_changed
            for evt in final_status_events:
                publish_deployment_status_changed(
                    course_id=str(course_id),
                    course_content_id=evt["course_content_id"],
                    deployment_id=evt["deployment_id"],
                    previous_status="deploying",
                    new_status=evt["new_status"],
                    version_tag=evt.get("version_tag"),
                    example_identifier=evt.get("example_identifier"),
                    deployment_message=evt.get("deployment_message"),
                    deployed_at=evt.get("deployed_at"),
                    workflow_id=workflow_id,
                )

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

            # Broadcast failure events after successful commit
            from computor_backend.websocket.event_publisher import publish_deployment_status_changed
            for deployment in failed_deployments:
                publish_deployment_status_changed(
                    course_id=str(course_id),
                    course_content_id=str(deployment.course_content_id),
                    deployment_id=str(deployment.id),
                    previous_status="deploying",
                    new_status="failed",
                    deployment_message=str(e)[:500],
                    version_tag=deployment.version_tag,
                    example_identifier=str(deployment.example_identifier) if deployment.example_identifier else None,
                    workflow_id=workflow_id,
                )
        except Exception as db_error:
            logger.error(f"Failed to update deployment statuses: {db_error}")

        return {
            "success": False,
            "processed_count": 0,
            "errors": [str(e)],
            "message": f"Failed to generate student template: {str(e)}"
        }


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


WORKFLOWS = [
    GenerateStudentTemplateWorkflowV2,
]

ACTIVITIES = [
    generate_student_template_activity_v2,
]
