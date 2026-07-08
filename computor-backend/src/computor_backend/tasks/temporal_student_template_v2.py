"""
Temporal workflows for generating student templates from Example Library.
Version 2: Fixed deployment status handling and sandbox restrictions.
"""
import asyncio
import logging
from datetime import timedelta
from typing import Dict, Any, List

from temporalio import workflow, activity

from .temporal_base import BaseWorkflow, WorkflowResult
from .git_ops import clone_or_init, commit_and_push, configure_identity
from .registry import register_task
from .student_template import (
    broadcast_deployment_events,
    collect_failed_events,
    fail_all_deploying,
    generate_main_readme,
    link_testing_service,
    mark_deployed,
    mark_deploying,
    mark_failed,
    push_reference_repo,
    resolve_deployment_directory,
    select_contents_to_process,
    select_deployments_for_release,
)
from .student_template.status import failed_event

logger = logging.getLogger(__name__)


def process_example_for_student_template_v2(
    example_files: Dict[str, bytes],
    target_path: Any,  # Path object
    course_content: Any,
    version: Any
) -> Dict[str, Any]:
    """
    Process example files for student template generation.
    File lists come from the ExampleVersion DB row (typed columns), not
    from re-parsing the workspace meta.yaml.

    Pure synchronous file I/O (no awaits): a plain ``def`` so the now-sync
    release activity can call it directly.
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

        # SAFETY: This function is the boundary between the full example bundle
        # (which contains solutions, tests, hints, and other instructor-only
        # material) and the student-facing template repo. It operates as a
        # strict allowlist. The ONLY files emitted are:
        #   1. README.md       <- content/index.md  (rename only; content/ itself never ships)
        #   2. README_<lang>.md <- content/index_<lang>.md  (same)
        #   3. additionalFiles  (from meta.yaml's typed columns)
        #   4. studentSubmissionFiles  (filled from studentTemplates or empty)
        #   5. content/mediaFiles/**  (figures the README references — copied to
        #      mediaFiles/** so the README's relative image links resolve)
        # The rest of content/ and the entire localTests/ directory must NEVER
        # appear in the student template.
        for filename, content in example_files.items():
            # Handle index*.md inside content/ — renamed to README.
            if filename == 'content/index.md':
                (target_path / 'README.md').write_bytes(content)
            elif filename.startswith('content/index_') and filename.endswith('.md'):
                lang_suffix = filename[len('content/index'):-3]  # '_de' from 'content/index_de.md'
                (target_path / f'README{lang_suffix}.md').write_bytes(content)
            elif filename.startswith('content/mediaFiles/'):
                # Figures referenced by the README. Copy under the assignment root
                # preserving the mediaFiles/ subpath (strip 'content/') so the
                # README's relative image links resolve. Public assets, not solutions.
                dest = target_path / filename[len('content/'):]  # e.g. 'mediaFiles/foo.png'
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(content)
            # Everything else under content/ or localTests/ is DROPPED.
            # No fallback, no implicit copy.

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
            # No meta.yaml — REFUSE. There is no safe fallback: an
            # allowlist-free copy would ship localTests/, content/, and
            # whatever else the example contains. localTests/ must NEVER
            # reach the student template under any circumstance.
            logger.error(
                f"Refusing to generate student template for {course_content.path}: "
                f"no meta.yaml fields populated on ExampleVersion. Fix the example."
            )
            return {
                "success": False,
                "error": (
                    f"meta.yaml missing/empty for {course_content.path}; "
                    "refusing to emit any files (no safe fallback exists)"
                ),
            }

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
    """Not implemented: examples are served from MinIO/S3, not git."""
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
def generate_student_template_activity_v2(
    course_id: str,
    student_template_url: str,
    assignments_url: str = None,
    workflow_id: str = None,
    force_redeploy: bool = False,
    release: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    """
    Generate student template repository from examples assigned to course content.

    BLOCKING activity: GitPython clone/commit/push and synchronous SQLAlchemy
    session work spanning the whole body. Runs as a plain ``def`` in the worker's
    thread pool (Worker(activity_executor=...)) so a multi-minute clone/push never
    stalls the event loop, heartbeats, or other activities. The one
    genuinely-async helper (``download_example_files``, async object-storage I/O)
    is driven with ``asyncio.run`` inside this thread (no running loop here); the
    sync helpers (status transitions, README, reference push, and the sync
    ``publish_deployment_status_changed`` broadcast) are called directly.

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
    # Import database dependencies inside activity (sandbox-safe)
    import os
    import tempfile
    from pathlib import Path
    from ..database import get_db_session
    from ..model.course import Course

    with get_db_session() as db:
      try:
        # A release selection restricts to specific contents; else status-based.
        selected_course_content_ids: List[str] = []
        if release:
            selected_course_content_ids = release.get("course_content_ids") or []

        # First, update all assigned deployments to 'deploying' status
        deployments_to_process = select_deployments_for_release(
            db, course_id, selected_course_content_ids, force_redeploy
        )
        deploying_events = mark_deploying(db, deployments_to_process, workflow_id)
        db.commit()

        # Broadcast deployment status changes after successful commit
        broadcast_deployment_events(course_id, deploying_events, workflow_id)
        logger.info(f"Updated {len(deployments_to_process)} deployments to 'deploying' status")

        # Get course details
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise ValueError(f"Course {course_id} not found")
        
        organization = course.organization

        # Resolve the push token + provider. Managed courses keep the token on the
        # bound GitServer (registry); legacy org-level GitLab keeps it in
        # organization.properties.gitlab (which wins here so mid-migration
        # courses keep releasing).
        from computor_backend.git_provider.token_resolution import resolve_course_push_credentials

        creds = resolve_course_push_credentials(db, course_id, prefer_org_token=True)
        gitlab_token = creds.token
        server_type = creds.server_type
        student_template_url = creds.rewrite_to_reachable(student_template_url)

        logger.info(f"Using student template URL: {student_template_url}")

        # Use temp directory for repository work
        with tempfile.TemporaryDirectory() as temp_dir:
            template_repo_path = os.path.join(temp_dir, "student-template")
            
            template_repo = clone_or_init(
                student_template_url, gitlab_token, server_type, template_repo_path
            )
            git_email, git_name = configure_identity(template_repo)

            # NOTE: We do NOT use the assignments repository here!
            # All example content comes directly from MinIO via download_example_files()
            # The assignments repository is managed separately by temporal_assignments_repository.py

            # REPOSITORY STATE VERIFICATION
            # Scan what's actually present in the cloned repository to detect state mismatches
            existing_directories = set()

            try:
                for item in os.listdir(template_repo_path):
                    item_path = os.path.join(template_repo_path, item)
                    if os.path.isdir(item_path) and item != '.git':
                        existing_directories.add(item)

                if template_repo.head.is_valid():
                    logger.info(f"Repository scan: Found {len(existing_directories)} existing directories, HEAD={template_repo.head.commit.hexsha[:8]}")
                else:
                    logger.info(f"Repository scan: Found {len(existing_directories)} existing directories (no commits yet)")
            except Exception as e:
                logger.warning(f"Failed to scan repository state: {e}. Proceeding without verification.")

            # Select the contents to process (incl. repo-state-mismatch re-deploys)
            course_contents, _state_mismatches = select_contents_to_process(
                db, course_id, selected_course_content_ids, force_redeploy, existing_directories
            )

            logger.info(f"Selected {len(course_contents)} course contents to process")
            
            if not course_contents:
                logger.warning(f"No course contents to deploy for course {course_id}. This will result in an empty student template.")
            
            # Process each CourseContent with an example
            processed_count = 0
            errors = []
            successfully_processed = []  # Track which content was successfully processed
            reference_files: Dict[str, dict] = {}  # target_dir -> {files, additional_files, submission_files} for the reference repo
            
            for content in course_contents:
                try:
                    if not content.deployment:
                        # Skip non-assigned items (e.g., container units)
                        logger.info(f"Skipping {content.path}: no deployment assigned")
                        continue

                    # Get deployment path (deployment_path, else example_identifier,
                    # else example.identifier); persist the resolved value.
                    directory_name = resolve_deployment_directory(content.deployment, persist=True)
                    if not directory_name:
                        error_msg = (
                            f"❌ CRITICAL: Cannot deploy {content.path} - no deployment_path, no example_identifier, "
                            f"and no example.identifier available. This CourseContentDeployment record is invalid. "
                            f"Deployment ID: {content.deployment.id}"
                        )
                        logger.error(error_msg)
                        errors.append(error_msg)

                        if content.deployment.deployment_status == "deploying":
                            mark_failed(
                                db, content.deployment,
                                "Cannot determine deployment directory: deployment_path, example_identifier, "
                                "and example.identifier are all NULL",
                                workflow_id,
                            )
                        continue

                    # Download files from example repository (MinIO or Git based on source_type)
                    # NOTE: We download directly from MinIO/ExampleRepository, NOT from assignments repo!
                    files: Dict[str, bytes] = {}
                    try:
                        if content.deployment.example_version:
                            example_repo = content.deployment.example_version.example.repository
                            # download_example_files returns files already scoped to the example version
                            # No filtering needed - the storage_path in MinIO already isolates this example
                            # async object-storage helper driven via asyncio.run (this activity is sync)
                            files = asyncio.run(download_example_files(example_repo, content.deployment.example_version))
                    except Exception as e:
                        logger.warning(f"Failed to load files from example repository for {content.path}: {e}")
                        files = {}

                    # Legacy fallback: link a testing service by language when
                    # the slug→service.id resolution didn't fire.
                    link_testing_service(db, content, files)

                    if not files:
                        # Strict mode: fail when example repository does not provide files
                        reason = "no files in example repository" if content.deployment.example_version else "no example version configured"
                        logger.error(f"Release failed for {content.path}: {reason}")
                        mark_failed(db, content.deployment, f"Example repository: {reason}", workflow_id)
                        errors.append(f"{str(content.path)}: {reason}")
                        continue
                    
                    logger.info(f"Downloaded {len(files)} files for {content.path}")
                    
                    # Determine target directory in student template
                    # Use the example identifier as directory name for better organization
                    target_dir = str(directory_name)
                    full_target_path = os.path.join(template_repo_path, target_dir)
                    # Snapshot the FULL files (before solution-stripping) so the reference
                    # repo can mirror them; recorded only after successful processing below.
                    full_files_snapshot = dict(files)
                    
                    # Process the example files for student template
                    # This function handles meta.yaml properties like studentSubmissionFiles,
                    # studentTemplates, additionalFiles, and content directory processing
                    # IMPORTANT: pass the ExampleVersion so the function can
                    # read its typed allowlist columns (additional_files,
                    # student_submission_files, student_templates). When this
                    # was None — regression in 41b6ba9 (2025-09-15) — every
                    # release fell through to the no-meta fallback and shipped
                    # the full example bundle minus things prefixed "test"
                    # (i.e. localTests/ leaked).
                    process_result = process_example_for_student_template_v2(
                        example_files=files,
                        target_path=Path(full_target_path),
                        course_content=content,
                        version=content.deployment.example_version,
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
                    # Collect this assignment's reference inputs (pushed after the
                    # template push, best-effort): the full files plus the typed
                    # file lists the reference converter needs.
                    _ev = content.deployment.example_version
                    reference_files[target_dir] = {
                        "files": full_files_snapshot,
                        "additional_files": list(getattr(_ev, "additional_files", None) or []),
                        "submission_files": list(getattr(_ev, "student_submission_files", None) or []),
                    }
                    
                except Exception as e:
                    error_msg = f"Failed to process {content.path}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    errors.append(error_msg)
                    
                    # Update deployment status to failed with history
                    if content.deployment:
                        mark_failed(db, content.deployment, str(e), workflow_id)

            # Don't commit yet - wait until after git operations

            # Generate main README.md with ALL deployed/deploying assignments
            # (generated BEFORE the final status update of this run).
            all_deployed_contents = generate_main_readme(db, course, template_repo_path)

            # Commit and push to Git if we processed content OR if README changed
            # This ensures README is always up-to-date even if no new deployments occurred
            git_push_successful = False
            if processed_count > 0 or (len(all_deployed_contents) > 0 and os.path.exists(os.path.join(template_repo_path, "README.md"))):
                try:
                    git_push_successful = commit_and_push(template_repo, "System Release")

                except Exception as e:
                    error_msg = f"Failed to commit/push changes: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    git_push_successful = False

            # ----- reference repo (full solutions) — best-effort, never blocks the template -----
            # Mirror the SAME assignments into the staff-only reference repo, but with the
            # FULL example content (solutions included). Any failure is logged and ignored:
            # the student template is the student-facing artifact and must not be held
            # hostage to the reference push.
            if reference_files:
                try:
                    from computor_backend.model.git_server import CourseGitBinding
                    ref_binding = (
                        db.query(CourseGitBinding)
                        .filter(CourseGitBinding.course_id == course_id)
                        .first()
                    )
                    push_reference_repo(ref_binding, reference_files, gitlab_token, server_type)
                except Exception as e:
                    logger.warning(f"Reference repo push failed (non-fatal) for course {course_id}: {e}")

            # Now update deployment statuses based on git push result. Only
            # deployments marked "deploying" at the start are transitioned.
            final_status_events = []

            if git_push_successful and processed_count > 0:
                try:
                    final_template_sha = template_repo.head.commit.hexsha
                    logger.info(f"Student-template repository now at commit: {final_template_sha[:8]}")
                except Exception as e:
                    logger.warning(f"Could not get repository commit SHA: {e}")
                    final_template_sha = None

                for content in successfully_processed:
                    if content.deployment and content.deployment.deployment_status == "deploying":
                        final_status_events.append(
                            mark_deployed(db, content, final_template_sha, workflow_id)
                        )
            else:
                # Git push failed - mark only the ones we're processing as failed
                for content in course_contents:
                    if content.deployment and content.deployment.deployment_status == "deploying":
                        mark_failed(db, content.deployment, "Git push failed", workflow_id)
                        final_status_events.append(failed_event(content))

            # Also collect any content that was marked as failed during processing
            # (directory resolution, file download, processing exceptions)
            final_status_events.extend(
                collect_failed_events(course_contents, final_status_events)
            )

            # Now commit database changes, then broadcast
            db.commit()
            broadcast_deployment_events(course_id, final_status_events, workflow_id)

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

        # Mark all 'deploying' deployments as failed and broadcast
        try:
            failed_events = fail_all_deploying(db, course_id, str(e), workflow_id)
            db.commit()
            broadcast_deployment_events(course_id, failed_events, workflow_id)
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

        invalid = self.require_params(params, 'course_id', 'student_template_url')
        if invalid:
            return invalid

        # Get workflow ID for tracking
        workflow_id = workflow.info().workflow_id

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

            result = await self.run_single_activity(
                generate_student_template_activity_v2,
                args=[course_id, student_template_url, assignments_url, workflow_id, force_redeploy, release],
                timeout=timedelta(minutes=30),
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


ACTIVITIES = [
    generate_student_template_activity_v2,
]
