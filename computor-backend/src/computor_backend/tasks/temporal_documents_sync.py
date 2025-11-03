"""
Temporal activity and workflow to sync documents repository from GitLab to filesystem.

This activity clones the documents repository from the course family's GitLab group
and syncs it to the shared documents directory for serving via static-server.
"""
from datetime import timedelta, datetime, timezone
from typing import Any, Dict, Optional
import os
import tempfile
import shutil
import logging
from pathlib import Path

from temporalio import workflow, activity
from temporalio.common import RetryPolicy

from .temporal_base import BaseWorkflow, WorkflowResult
from .registry import register_task

logger = logging.getLogger(__name__)


@activity.defn(name="sync_documents_repository")
async def sync_documents_repository_activity(
    course_family_id: str,
    force_update: bool = False
) -> Dict[str, Any]:
    """
    Sync documents repository from GitLab to shared filesystem.

    Args:
        course_family_id: CourseFamily ID
        force_update: If True, delete and re-clone; if False, just git pull

    Returns:
        Dict with success status, synced file count, and any errors
    """
    import git
    from ..database import get_db
    from ..model.course import CourseFamily, Organization
    from ..settings import Settings
    from ..utils.docker_utils import transform_localhost_url

    settings = Settings()
    db_gen = next(get_db())
    db = db_gen

    result = {
        "success": False,
        "course_family_id": course_family_id,
        "synced_files": 0,
        "error": None,
        "documents_url": None,
        "target_path": None
    }

    try:
        # Fetch course family with organization
        course_family = db.query(CourseFamily).filter(
            CourseFamily.id == course_family_id
        ).first()

        if not course_family:
            result["error"] = f"CourseFamily {course_family_id} not found"
            return result

        # Get organization
        organization = db.query(Organization).filter(
            Organization.id == course_family.organization_id
        ).first()

        if not organization:
            result["error"] = f"Organization not found for CourseFamily {course_family_id}"
            return result

        # Get GitLab configuration from organization
        org_props = organization.properties or {}
        gitlab_config = org_props.get("gitlab", {})
        gitlab_url = gitlab_config.get("url")

        # Get encrypted token
        gitlab_token = None
        if gitlab_config.get("token"):
            try:
                from computor_types.tokens import decrypt_api_key
                gitlab_token = decrypt_api_key(gitlab_config["token"])
            except Exception as e:
                logger.warning(f"Could not decrypt GitLab token: {e}")

        if not gitlab_url:
            result["error"] = "GitLab URL not configured for organization"
            return result

        # Get course family GitLab path
        family_props = course_family.properties or {}
        family_gitlab = family_props.get("gitlab", {})
        full_path = family_gitlab.get("full_path")

        if not full_path:
            result["error"] = f"GitLab full_path not found for CourseFamily {course_family.path}"
            return result

        # Construct documents repository URL
        # Format: https://gitlab.com/org/family/documents.git
        documents_url = f"{gitlab_url}/{full_path}/documents.git"
        documents_url = transform_localhost_url(documents_url)
        result["documents_url"] = documents_url

        # Construct target path on filesystem
        # Format: ${SYSTEM_DEPLOYMENT_PATH}/shared/documents/org_path/family_path/
        if not settings.API_LOCAL_STORAGE_DIR:
            result["error"] = "API_LOCAL_STORAGE_DIR not configured"
            return result

        target_base = os.path.join(settings.API_LOCAL_STORAGE_DIR, "documents")
        target_path = os.path.join(target_base, str(organization.path), str(course_family.path))
        result["target_path"] = target_path

        # Ensure parent directory exists
        os.makedirs(os.path.dirname(target_path), exist_ok=True)

        # Prepare authenticated URL if token available
        auth_url = documents_url
        if gitlab_token and 'http' in documents_url:
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(documents_url)
            auth_netloc = f"oauth2:{gitlab_token}@{parsed.hostname}"
            if parsed.port:
                auth_netloc += f":{parsed.port}"
            auth_url = urlunparse((parsed.scheme, auth_netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))

        # Define blacklist of files/directories to exclude from sync
        # These are sensitive or unnecessary files that should not be exposed
        SYNC_BLACKLIST = {
            '.git',           # Git metadata
            '.gitignore',     # Git configuration (not needed for static serving)
            '.gitlab-ci.yml', # CI/CD configuration
            '.DS_Store',      # macOS metadata
            'Thumbs.db',      # Windows metadata
            '.env',           # Environment variables (security)
            '.env.local',     # Environment variables
            'node_modules',   # Dependencies
            '__pycache__',    # Python cache
            '*.pyc',          # Python compiled files
            '.vscode',        # Editor settings
            '.idea',          # Editor settings
        }

        # Special case: exclude README.md only from root directory
        ROOT_BLACKLIST = {
            'README.md',      # Root README (repository description, not course document)
        }

        def should_exclude(name: str, blacklist: set) -> bool:
            """Check if a file/directory should be excluded based on blacklist."""
            # Direct match
            if name in blacklist:
                return True
            # Pattern match (e.g., *.pyc)
            import fnmatch
            for pattern in blacklist:
                if fnmatch.fnmatch(name, pattern):
                    return True
            return False

        def copy_tree_filtered(src: str, dst: str, blacklist: set, root_src: str = None):
            """
            Copy directory tree while filtering out blacklisted items.

            Args:
                src: Source directory
                dst: Destination directory
                blacklist: Set of items to exclude everywhere
                root_src: Original root source directory (to detect root-level files)
            """
            # Track root directory for special exclusions
            if root_src is None:
                root_src = src

            is_root = (src == root_src)

            os.makedirs(dst, exist_ok=True)

            for item in os.listdir(src):
                # Skip blacklisted items
                if should_exclude(item, blacklist):
                    logger.debug(f"Skipping blacklisted item: {item}")
                    continue

                # Skip root-level README.md
                if is_root and should_exclude(item, ROOT_BLACKLIST):
                    logger.debug(f"Skipping root-level file: {item}")
                    continue

                src_path = os.path.join(src, item)
                dst_path = os.path.join(dst, item)

                if os.path.isdir(src_path):
                    # Recursively copy directory
                    copy_tree_filtered(src_path, dst_path, blacklist, root_src)
                else:
                    # Copy file
                    shutil.copy2(src_path, dst_path)

        # Create temporary directory for cloning
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_repo_path = os.path.join(temp_dir, "documents")

            # Clone the repository
            try:
                logger.info(f"Attempting to clone documents repository: {documents_url}")
                repo = git.Repo.clone_from(auth_url, temp_repo_path)
                logger.info(f"Successfully cloned documents repository")
            except git.exc.GitCommandError as e:
                # Repository might not exist yet
                result["error"] = f"Failed to clone documents repository: {str(e)}"
                result["success"] = True  # Not an error if repo doesn't exist yet
                result["synced_files"] = 0
                logger.warning(result["error"])
                return result

            # Clear target directory if force_update is True
            if os.path.exists(target_path) and force_update:
                logger.info(f"Force update: removing existing directory {target_path}")
                shutil.rmtree(target_path)

            # Copy files from temp to target, excluding blacklisted items
            logger.info(f"Syncing files to {target_path} (excluding: {', '.join(SYNC_BLACKLIST)})")
            copy_tree_filtered(temp_repo_path, target_path, SYNC_BLACKLIST)

            # Count synced files
            file_count = sum(len(files) for _, _, files in os.walk(target_path))
            result["synced_files"] = file_count

            logger.info(f"Successfully synced {file_count} files to {target_path}")

        result["success"] = True
        return result

    except Exception as e:
        logger.exception(f"Error syncing documents repository: {e}")
        result["error"] = str(e)
        return result

    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass


@workflow.defn(name="SyncDocumentsRepositoryWorkflow")
class SyncDocumentsRepositoryWorkflow(BaseWorkflow):
    """Workflow to sync documents repository from GitLab to filesystem."""

    @workflow.run
    async def run(self, course_family_id: str, force_update: bool = False) -> WorkflowResult:
        """
        Execute the documents sync workflow.

        Args:
            course_family_id: CourseFamily ID
            force_update: If True, delete and re-clone; if False, just update

        Returns:
            WorkflowResult with sync status
        """
        workflow_id = workflow.info().workflow_id

        logger.info(f"Starting documents sync workflow for CourseFamily {course_family_id}")

        try:
            # Execute the sync activity
            result = await workflow.execute_activity(
                sync_documents_repository_activity,
                args=[course_family_id, force_update],
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=RetryPolicy(
                    maximum_attempts=3,
                    initial_interval=timedelta(seconds=5),
                    maximum_interval=timedelta(seconds=30),
                    backoff_coefficient=2.0
                )
            )

            if result["success"]:
                return WorkflowResult(
                    success=True,
                    message=f"Synced {result['synced_files']} files from documents repository",
                    data={
                        "course_family_id": course_family_id,
                        "synced_files": result["synced_files"],
                        "documents_url": result["documents_url"],
                        "target_path": result["target_path"]
                    }
                )
            else:
                return WorkflowResult(
                    success=False,
                    message=f"Failed to sync documents: {result.get('error', 'Unknown error')}",
                    data=result
                )

        except Exception as e:
            logger.exception(f"Documents sync workflow failed: {e}")
            return WorkflowResult(
                success=False,
                message=f"Workflow error: {str(e)}",
                data={"error": str(e)}
            )


# Register the task
register_task(
    "sync_documents_repository",
    SyncDocumentsRepositoryWorkflow,
    "Sync documents repository from GitLab to filesystem"
)
