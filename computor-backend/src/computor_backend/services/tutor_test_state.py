"""
Redis state management for tutor tests.

This module manages ephemeral state for tutor test runs using Redis.
All keys have TTL (1 hour) for automatic cleanup.

Key structure:
- tutor_test:{test_id}:meta   -> JSON metadata
- tutor_test:{test_id}:status -> Status string
- tutor_test:{test_id}:result -> JSON test results (when completed)

No database records are created for tutor tests.
"""

import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)

# TTL for tutor test keys (1 hour in seconds)
TUTOR_TEST_TTL = 3600

# Key prefix (no "computor:" - that's only used by the Cache class)
KEY_PREFIX = "tutor_test"


class TutorTestStatus(str, Enum):
    """Status values for tutor tests."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


def _get_meta_key(test_id: str | UUID) -> str:
    """Get Redis key for test metadata."""
    return f"{KEY_PREFIX}:{str(test_id)}:meta"


def _get_status_key(test_id: str | UUID) -> str:
    """Get Redis key for test status."""
    return f"{KEY_PREFIX}:{str(test_id)}:status"


def _get_result_key(test_id: str | UUID) -> str:
    """Get Redis key for test results."""
    return f"{KEY_PREFIX}:{str(test_id)}:result"


async def create_tutor_test_entry(
    redis_client,
    test_id: str | UUID,
    user_id: str | UUID,
    course_content_id: str | UUID,
    testing_service_id: str | UUID,
    testing_service_slug: str,
    course_id: str | UUID,
) -> dict:
    """
    Create a new tutor test entry in Redis.

    Args:
        redis_client: Async Redis client
        test_id: Unique test identifier
        user_id: User running the test
        course_content_id: The assignment being tested
        testing_service_id: Testing service ID
        testing_service_slug: Testing service slug (e.g., "python", "matlab")
        course_id: The course ID

    Returns:
        Dict with the created test info
    """
    test_id_str = str(test_id)
    created_at = datetime.now(timezone.utc).isoformat()

    metadata = {
        "test_id": test_id_str,
        "user_id": str(user_id),
        "course_content_id": str(course_content_id),
        "course_id": str(course_id),
        "testing_service_id": str(testing_service_id),
        "testing_service_slug": testing_service_slug,
        "created_at": created_at,
        "started_at": None,
        "finished_at": None,
    }

    # Use pipeline for atomic operations
    pipe = redis_client.pipeline()

    # Store metadata
    pipe.set(
        _get_meta_key(test_id),
        json.dumps(metadata),
        ex=TUTOR_TEST_TTL
    )

    # Set initial status
    pipe.set(
        _get_status_key(test_id),
        TutorTestStatus.PENDING.value,
        ex=TUTOR_TEST_TTL
    )

    await pipe.execute()

    logger.info(f"Created tutor test entry: {test_id_str}")

    return {
        "test_id": test_id_str,
        "status": TutorTestStatus.PENDING.value,
        "created_at": created_at,
    }


async def get_tutor_test_status(
    redis_client,
    test_id: str | UUID,
) -> Optional[str]:
    """
    Get the current status of a tutor test.

    Args:
        redis_client: Async Redis client
        test_id: The test ID

    Returns:
        Status string or None if not found
    """
    status = await redis_client.get(_get_status_key(test_id))
    return status if status else None


async def get_tutor_test_metadata(
    redis_client,
    test_id: str | UUID,
) -> Optional[dict]:
    """
    Get metadata for a tutor test.

    Args:
        redis_client: Async Redis client
        test_id: The test ID

    Returns:
        Metadata dict or None if not found
    """
    data = await redis_client.get(_get_meta_key(test_id))
    if data:
        return json.loads(data)
    return None


async def get_tutor_test_result(
    redis_client,
    test_id: str | UUID,
) -> Optional[dict]:
    """
    Get test results for a tutor test.

    Args:
        redis_client: Async Redis client
        test_id: The test ID

    Returns:
        Results dict or None if not found/not completed
    """
    data = await redis_client.get(_get_result_key(test_id))
    if data:
        return json.loads(data)
    return None


async def get_tutor_test_full(
    redis_client,
    test_id: str | UUID,
) -> Optional[dict]:
    """
    Get full tutor test info including status, metadata, and results.

    Args:
        redis_client: Async Redis client
        test_id: The test ID

    Returns:
        Combined dict with all test info, or None if not found
    """
    # Get all keys in one round trip
    pipe = redis_client.pipeline()
    pipe.get(_get_status_key(test_id))
    pipe.get(_get_meta_key(test_id))
    pipe.get(_get_result_key(test_id))

    status, meta_raw, result_raw = await pipe.execute()

    if not status and not meta_raw:
        return None

    response = {
        "test_id": str(test_id),
        "status": status if status else TutorTestStatus.PENDING.value,
    }

    if meta_raw:
        metadata = json.loads(meta_raw)
        response.update({
            "user_id": metadata.get("user_id"),
            "course_content_id": metadata.get("course_content_id"),
            "course_id": metadata.get("course_id"),
            "testing_service_slug": metadata.get("testing_service_slug"),
            "created_at": metadata.get("created_at"),
            "started_at": metadata.get("started_at"),
            "finished_at": metadata.get("finished_at"),
        })

    if result_raw:
        response["result"] = json.loads(result_raw)

    return response


async def update_tutor_test_status(
    redis_client,
    test_id: str | UUID,
    status: TutorTestStatus,
    started_at: Optional[datetime] = None,
    finished_at: Optional[datetime] = None,
) -> bool:
    """
    Update the status of a tutor test.

    Args:
        redis_client: Async Redis client
        test_id: The test ID
        status: New status
        started_at: Optional start timestamp
        finished_at: Optional finish timestamp

    Returns:
        True if updated, False if test not found
    """
    # Check if test exists
    existing = await redis_client.get(_get_status_key(test_id))
    if not existing:
        return False

    pipe = redis_client.pipeline()

    # Update status with TTL refresh
    pipe.set(
        _get_status_key(test_id),
        status.value,
        ex=TUTOR_TEST_TTL
    )

    # Update metadata timestamps if provided
    meta_raw = await redis_client.get(_get_meta_key(test_id))
    if meta_raw:
        metadata = json.loads(meta_raw)
        if started_at:
            metadata["started_at"] = started_at.isoformat()
        if finished_at:
            metadata["finished_at"] = finished_at.isoformat()

        pipe.set(
            _get_meta_key(test_id),
            json.dumps(metadata),
            ex=TUTOR_TEST_TTL
        )

    await pipe.execute()

    logger.info(f"Updated tutor test {test_id} status to {status.value}")
    return True


async def store_tutor_test_result(
    redis_client,
    test_id: str | UUID,
    result: dict,
    status: TutorTestStatus = TutorTestStatus.COMPLETED,
) -> bool:
    """
    Store test results and update status.

    Args:
        redis_client: Async Redis client
        test_id: The test ID
        result: Test results dictionary
        status: Final status (COMPLETED or FAILED)

    Returns:
        True if stored, False if test not found
    """
    # Check if test exists
    existing = await redis_client.get(_get_status_key(test_id))
    if not existing:
        return False

    finished_at = datetime.now(timezone.utc)

    pipe = redis_client.pipeline()

    # Store results
    pipe.set(
        _get_result_key(test_id),
        json.dumps(result),
        ex=TUTOR_TEST_TTL
    )

    # Update status
    pipe.set(
        _get_status_key(test_id),
        status.value,
        ex=TUTOR_TEST_TTL
    )

    # Update metadata with finished_at
    meta_raw = await redis_client.get(_get_meta_key(test_id))
    if meta_raw:
        metadata = json.loads(meta_raw)
        metadata["finished_at"] = finished_at.isoformat()
        pipe.set(
            _get_meta_key(test_id),
            json.dumps(metadata),
            ex=TUTOR_TEST_TTL
        )

    await pipe.execute()

    logger.info(f"Stored tutor test result for {test_id}, status: {status.value}")
    return True


async def tutor_test_exists(
    redis_client,
    test_id: str | UUID,
) -> bool:
    """
    Check if a tutor test exists.

    Args:
        redis_client: Async Redis client
        test_id: The test ID

    Returns:
        True if exists, False otherwise
    """
    exists = await redis_client.exists(_get_status_key(test_id))
    return bool(exists)


async def refresh_tutor_test_ttl(
    redis_client,
    test_id: str | UUID,
) -> bool:
    """
    Refresh TTL for all keys of a tutor test.

    Useful for long-running tests to prevent premature expiration.

    Args:
        redis_client: Async Redis client
        test_id: The test ID

    Returns:
        True if refreshed, False if test not found
    """
    pipe = redis_client.pipeline()
    pipe.expire(_get_status_key(test_id), TUTOR_TEST_TTL)
    pipe.expire(_get_meta_key(test_id), TUTOR_TEST_TTL)
    pipe.expire(_get_result_key(test_id), TUTOR_TEST_TTL)

    results = await pipe.execute()
    # At least status key should exist
    return bool(results[0])
