"""
Service for storing and retrieving result JSON data in MinIO.

This module handles the storage of large, unstructured result JSON data
that was previously stored in the PostgreSQL database.

Storage structure:
- Bucket: "results"
- Path: {result_id}/result.json
"""

import json
import logging
from io import BytesIO
from typing import Optional
from uuid import UUID

from .storage_service import get_storage_service
from ..api.exceptions import NotFoundException

logger = logging.getLogger(__name__)

# Dedicated bucket for test results
RESULTS_BUCKET = "results"


def get_result_json_key(result_id: str | UUID) -> str:
    """
    Get the MinIO object key for a result's JSON data.

    Args:
        result_id: The result ID (UUID as string or UUID object)

    Returns:
        The object key path: {result_id}/result.json
    """
    return f"{str(result_id)}/result.json"


async def store_result_json(result_id: str | UUID, result_json: dict) -> str:
    """
    Store result JSON data in MinIO.

    Args:
        result_id: The result ID
        result_json: The JSON data to store (will be serialized)

    Returns:
        The object key where the JSON was stored

    Raises:
        ServiceUnavailableException: If MinIO storage fails
    """
    storage = get_storage_service()
    object_key = get_result_json_key(result_id)

    # Serialize JSON to bytes
    json_bytes = json.dumps(result_json, indent=2).encode('utf-8')
    json_stream = BytesIO(json_bytes)

    # Upload to MinIO in dedicated "results" bucket
    await storage.upload_file(
        file_data=json_stream,
        object_key=object_key,
        bucket_name=RESULTS_BUCKET,
        content_type="application/json",
        metadata={
            "result_id": str(result_id),
            "type": "result_json"
        }
    )

    logger.info(f"Stored result JSON for result {result_id} in {RESULTS_BUCKET}/{object_key}")
    return object_key


async def retrieve_result_json(result_id: str | UUID) -> Optional[dict]:
    """
    Retrieve result JSON data from MinIO.

    Args:
        result_id: The result ID

    Returns:
        The deserialized JSON data, or None if not found

    Note:
        Returns None instead of raising NotFoundException to allow
        graceful handling of missing JSON data.
    """
    storage = get_storage_service()
    object_key = get_result_json_key(result_id)

    try:
        # Download from MinIO "results" bucket
        json_bytes = await storage.download_file(object_key, bucket_name=RESULTS_BUCKET)

        # Deserialize JSON
        result_json = json.loads(json_bytes.decode('utf-8'))

        logger.debug(f"Retrieved result JSON for result {result_id}")
        return result_json

    except NotFoundException:
        logger.debug(f"No result JSON found for result {result_id}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode result JSON for result {result_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error retrieving result JSON for result {result_id}: {e}")
        return None


async def delete_result_json(result_id: str | UUID) -> bool:
    """
    Delete result JSON data from MinIO.

    Args:
        result_id: The result ID

    Returns:
        True if deleted successfully, False if not found

    Note:
        Does not raise exceptions - returns False if object doesn't exist.
    """
    storage = get_storage_service()
    object_key = get_result_json_key(result_id)

    try:
        await storage.delete_file(object_key, bucket_name=RESULTS_BUCKET)
        logger.info(f"Deleted result JSON for result {result_id}")
        return True
    except NotFoundException:
        logger.debug(f"No result JSON to delete for result {result_id}")
        return False
    except Exception as e:
        logger.error(f"Error deleting result JSON for result {result_id}: {e}")
        return False


async def update_result_json(result_id: str | UUID, result_json: dict) -> str:
    """
    Update (replace) result JSON data in MinIO.

    This is an alias for store_result_json since MinIO overwrites by default.

    Args:
        result_id: The result ID
        result_json: The new JSON data to store

    Returns:
        The object key where the JSON was stored
    """
    return await store_result_json(result_id, result_json)


def get_result_artifact_key(result_id: str | UUID, filename: str) -> str:
    """
    Get the MinIO object key for a result artifact.

    Args:
        result_id: The result ID (UUID as string or UUID object)
        filename: The artifact filename

    Returns:
        The object key path: {result_id}/artifacts/{filename}
    """
    return f"{str(result_id)}/artifacts/{filename}"


async def store_result_artifact(
    result_id: str | UUID,
    filename: str,
    file_data: bytes,
    content_type: Optional[str] = None,
) -> dict:
    """
    Store a result artifact file in MinIO.

    Args:
        result_id: The result ID
        filename: The artifact filename
        file_data: The file content as bytes
        content_type: Optional MIME type (will be guessed if not provided)

    Returns:
        Dict with storage info: object_key, bucket_name, file_size, content_type

    Raises:
        ServiceUnavailableException: If MinIO storage fails
    """
    import mimetypes

    storage = get_storage_service()
    object_key = get_result_artifact_key(result_id, filename)

    # Guess content type if not provided
    if content_type is None:
        content_type, _ = mimetypes.guess_type(filename)
        if content_type is None:
            content_type = "application/octet-stream"

    # Upload to MinIO in dedicated "results" bucket
    file_stream = BytesIO(file_data)
    await storage.upload_file(
        file_data=file_stream,
        object_key=object_key,
        bucket_name=RESULTS_BUCKET,
        content_type=content_type,
        metadata={
            "result_id": str(result_id),
            "type": "result_artifact",
            "filename": filename,
        }
    )

    logger.info(f"Stored result artifact '{filename}' for result {result_id} in {RESULTS_BUCKET}/{object_key}")

    return {
        "object_key": object_key,
        "bucket_name": RESULTS_BUCKET,
        "file_size": len(file_data),
        "content_type": content_type,
    }


async def list_result_artifacts(result_id: str | UUID) -> list[dict]:
    """
    List all artifacts for a result.

    Args:
        result_id: The result ID

    Returns:
        List of dicts with artifact info (object_key, size, content_type, last_modified)
    """
    storage = get_storage_service()
    prefix = f"{str(result_id)}/artifacts/"

    try:
        objects = await storage.list_objects(
            bucket_name=RESULTS_BUCKET,
            prefix=prefix,
            recursive=True,
        )

        return [
            {
                "object_key": obj.object_name,
                "filename": obj.object_name.split("/")[-1],
                "size": obj.size,
                "last_modified": obj.last_modified,
            }
            for obj in objects
        ]
    except Exception as e:
        logger.error(f"Error listing result artifacts for result {result_id}: {e}")
        return []


async def retrieve_result_artifact(result_id: str | UUID, filename: str) -> Optional[bytes]:
    """
    Retrieve a result artifact from MinIO.

    Args:
        result_id: The result ID
        filename: The artifact filename

    Returns:
        The file content as bytes, or None if not found
    """
    storage = get_storage_service()
    object_key = get_result_artifact_key(result_id, filename)

    try:
        data = await storage.download_file(object_key, bucket_name=RESULTS_BUCKET)
        logger.debug(f"Retrieved result artifact '{filename}' for result {result_id}")
        return data
    except NotFoundException:
        logger.debug(f"No result artifact '{filename}' found for result {result_id}")
        return None
    except Exception as e:
        logger.error(f"Error retrieving result artifact '{filename}' for result {result_id}: {e}")
        return None


async def delete_result_artifacts(result_id: str | UUID) -> int:
    """
    Delete all artifacts for a result.

    Args:
        result_id: The result ID

    Returns:
        Number of artifacts deleted
    """
    storage = get_storage_service()
    prefix = f"{str(result_id)}/artifacts/"
    deleted_count = 0

    try:
        objects = await storage.list_objects(
            bucket_name=RESULTS_BUCKET,
            prefix=prefix,
            recursive=True,
        )

        for obj in objects:
            try:
                await storage.delete_file(obj.object_name, bucket_name=RESULTS_BUCKET)
                deleted_count += 1
                logger.debug(f"Deleted result artifact: {obj.object_name}")
            except Exception as e:
                logger.warning(f"Failed to delete artifact {obj.object_name}: {e}")

        logger.info(f"Deleted {deleted_count} artifacts for result {result_id}")
        return deleted_count
    except Exception as e:
        logger.error(f"Error deleting result artifacts for result {result_id}: {e}")
        return deleted_count
