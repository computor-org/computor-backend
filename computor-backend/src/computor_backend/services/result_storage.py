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
