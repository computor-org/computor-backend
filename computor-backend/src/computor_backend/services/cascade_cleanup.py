"""
Service for cleaning up MinIO storage during cascade deletion operations.

This module provides helper functions to remove storage objects when
deleting courses, organizations, or examples.

Storage structure:
- Submissions: "submissions" bucket at {bucket}/{object_key}
- Results: "results" bucket at {result_id}/result.json and {result_id}/artifacts/*
- Examples: Variable bucket/path based on repository configuration
"""

import logging
from typing import List, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from .storage_service import StorageService, get_storage_service
from .result_storage import RESULTS_BUCKET, delete_result_json, delete_result_artifacts
from ..api.exceptions import NotFoundException

logger = logging.getLogger(__name__)

# Default bucket for submission artifacts
SUBMISSIONS_BUCKET = "submissions"


async def cleanup_submission_artifact(
    bucket_name: str,
    object_key: str,
    storage: StorageService | None = None
) -> bool:
    """
    Delete a single submission artifact from MinIO.

    Args:
        bucket_name: The bucket containing the artifact
        object_key: The object key path
        storage: Optional storage service instance

    Returns:
        True if deleted, False if not found or error
    """
    if storage is None:
        storage = get_storage_service()

    try:
        await storage.delete_file(object_key, bucket_name=bucket_name)
        logger.debug(f"Deleted submission artifact: {bucket_name}/{object_key}")
        return True
    except NotFoundException:
        logger.debug(f"Submission artifact not found: {bucket_name}/{object_key}")
        return False
    except Exception as e:
        logger.warning(f"Error deleting submission artifact {bucket_name}/{object_key}: {e}")
        return False


async def cleanup_submission_artifacts_batch(
    artifacts: List[Tuple[str, str]],
    storage: StorageService | None = None
) -> int:
    """
    Delete multiple submission artifacts from MinIO.

    Args:
        artifacts: List of (bucket_name, object_key) tuples
        storage: Optional storage service instance

    Returns:
        Number of artifacts successfully deleted
    """
    if storage is None:
        storage = get_storage_service()

    deleted_count = 0
    for bucket_name, object_key in artifacts:
        if await cleanup_submission_artifact(bucket_name, object_key, storage):
            deleted_count += 1

    logger.info(f"Deleted {deleted_count}/{len(artifacts)} submission artifacts")
    return deleted_count


async def cleanup_result_storage(result_id: str | UUID) -> int:
    """
    Delete all MinIO objects for a result (result.json and artifacts).

    Args:
        result_id: The result ID

    Returns:
        Number of objects deleted
    """
    deleted_count = 0

    # Delete result JSON
    if await delete_result_json(result_id):
        deleted_count += 1

    # Delete result artifacts
    deleted_count += await delete_result_artifacts(result_id)

    return deleted_count


async def cleanup_results_batch(
    result_ids: List[str | UUID],
    storage: StorageService | None = None
) -> int:
    """
    Delete all MinIO objects for multiple results.

    Args:
        result_ids: List of result IDs
        storage: Optional storage service instance (not used, but kept for consistency)

    Returns:
        Total number of objects deleted
    """
    total_deleted = 0

    for result_id in result_ids:
        deleted = await cleanup_result_storage(result_id)
        total_deleted += deleted

    logger.info(f"Deleted storage for {len(result_ids)} results ({total_deleted} objects)")
    return total_deleted


async def cleanup_example_version_storage(
    storage_path: str,
    bucket_name: str,
    storage: StorageService | None = None
) -> int:
    """
    Delete all MinIO objects for an example version.

    Args:
        storage_path: The storage path prefix for the version
        bucket_name: The bucket containing the example
        storage: Optional storage service instance

    Returns:
        Number of objects deleted
    """
    if storage is None:
        storage = get_storage_service()

    deleted_count = 0

    try:
        # List all objects under the storage path
        objects = await storage.list_objects(
            bucket_name=bucket_name,
            prefix=storage_path,
            recursive=True
        )

        for obj in objects:
            try:
                await storage.delete_file(obj.object_name, bucket_name=bucket_name)
                deleted_count += 1
                logger.debug(f"Deleted example file: {bucket_name}/{obj.object_name}")
            except Exception as e:
                logger.warning(f"Failed to delete example file {obj.object_name}: {e}")

        logger.info(f"Deleted {deleted_count} files for example version at {bucket_name}/{storage_path}")
    except NotFoundException:
        logger.debug(f"Example storage not found: {bucket_name}/{storage_path}")
    except Exception as e:
        logger.warning(f"Error listing example version storage {bucket_name}/{storage_path}: {e}")

    return deleted_count


async def cleanup_example_versions_batch(
    versions: List[Tuple[str, str]],
    storage: StorageService | None = None
) -> int:
    """
    Delete storage for multiple example versions.

    Args:
        versions: List of (storage_path, bucket_name) tuples
        storage: Optional storage service instance

    Returns:
        Total number of objects deleted
    """
    if storage is None:
        storage = get_storage_service()

    total_deleted = 0

    for storage_path, bucket_name in versions:
        if storage_path and bucket_name:
            deleted = await cleanup_example_version_storage(storage_path, bucket_name, storage)
            total_deleted += deleted

    logger.info(f"Deleted storage for {len(versions)} example versions ({total_deleted} objects)")
    return total_deleted


async def cleanup_submission_group_by_prefix(
    submission_group_id: str | UUID,
    bucket_name: str = SUBMISSIONS_BUCKET,
    storage: StorageService | None = None
) -> int:
    """
    Delete all submission artifacts for a submission group by listing objects with prefix.

    This is used when we don't have the exact object keys stored in the database
    but know the submission group ID.

    Args:
        submission_group_id: The submission group ID
        bucket_name: The bucket containing submissions (default: "submissions")
        storage: Optional storage service instance

    Returns:
        Number of objects deleted
    """
    if storage is None:
        storage = get_storage_service()

    deleted_count = 0
    prefix = f"{str(submission_group_id)}/"

    try:
        objects = await storage.list_objects(
            bucket_name=bucket_name,
            prefix=prefix,
            recursive=True
        )

        for obj in objects:
            try:
                await storage.delete_file(obj.object_name, bucket_name=bucket_name)
                deleted_count += 1
                logger.debug(f"Deleted submission file: {bucket_name}/{obj.object_name}")
            except Exception as e:
                logger.warning(f"Failed to delete submission file {obj.object_name}: {e}")

        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} files for submission group {submission_group_id}")
    except NotFoundException:
        logger.debug(f"Submission group storage not found: {bucket_name}/{prefix}")
    except Exception as e:
        logger.warning(f"Error listing submission group storage {bucket_name}/{prefix}: {e}")

    return deleted_count


def collect_artifact_storage_info(
    db: Session,
    submission_group_ids: List[str]
) -> List[Tuple[str, str]]:
    """
    Collect storage info for submission artifacts from the database.

    Args:
        db: Database session
        submission_group_ids: List of submission group IDs

    Returns:
        List of (bucket_name, object_key) tuples
    """
    from ..model.artifact import SubmissionArtifact

    if not submission_group_ids:
        return []

    artifacts = db.query(
        SubmissionArtifact.bucket_name,
        SubmissionArtifact.object_key
    ).filter(
        SubmissionArtifact.submission_group_id.in_(submission_group_ids)
    ).all()

    return [(a.bucket_name, a.object_key) for a in artifacts]


def collect_result_artifact_storage_info(
    db: Session,
    result_ids: List[str]
) -> List[Tuple[str, str]]:
    """
    Collect storage info for result artifacts from the database.

    Args:
        db: Database session
        result_ids: List of result IDs

    Returns:
        List of (bucket_name, object_key) tuples
    """
    from ..model.artifact import ResultArtifact

    if not result_ids:
        return []

    artifacts = db.query(
        ResultArtifact.bucket_name,
        ResultArtifact.object_key
    ).filter(
        ResultArtifact.result_id.in_(result_ids)
    ).all()

    return [(a.bucket_name, a.object_key) for a in artifacts]
