"""
Tutor testing workflows and activities for Temporal.

This module handles testing of tutor-uploaded code against reference examples.
Unlike student testing, tutor tests:
- Don't create database records (state in Redis only)
- Store files in 'tutor-tests' bucket (with lifecycle cleanup)
- Are ephemeral (TTL-based expiration)

Reuses activities from temporal_student_testing where possible.
"""

import os
import json
import tempfile
import shutil
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

from temporalio import workflow, activity
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

from .temporal_base import BaseWorkflow, WorkflowResult
from .registry import register_task

# Reuse from student testing
from .temporal_student_testing import (
    fetch_example_version_with_dependencies,
    execute_tests_activity,
    EXAMPLE_CACHE_DIR,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Activities
# ============================================================================

@activity.defn(name="fetch_tutor_test_input")
async def fetch_tutor_test_input(
    test_id: str,
    target_dir: str,
) -> Dict[str, Any]:
    """
    Fetch tutor test input files from MinIO to local directory.

    Args:
        test_id: The tutor test ID
        target_dir: Directory to extract files to

    Returns:
        Dict with:
            - tutor_path: Path to extracted files
            - test_id: The test ID
    """
    from computor_backend.services.tutor_test_storage import (
        extract_tutor_test_input_to_directory
    )

    logger.info(f"Fetching tutor test input for {test_id}")

    try:
        tutor_path = await extract_tutor_test_input_to_directory(
            test_id=test_id,
            target_dir=target_dir,
        )

        logger.info(f"Extracted tutor test input to {tutor_path}")
        logger.info(f"  Contents: {os.listdir(tutor_path)}")

        return {
            "tutor_path": tutor_path,
            "test_id": test_id,
        }

    except Exception as e:
        logger.error(f"Failed to fetch tutor test input: {e}")
        raise ApplicationError(message=str(e))


@activity.defn(name="update_tutor_test_status_activity")
async def update_tutor_test_status_activity(
    test_id: str,
    status: str,
    redis_config: Dict[str, Any],
    started_at: Optional[str] = None,
    finished_at: Optional[str] = None,
) -> bool:
    """
    Update tutor test status in Redis.

    Args:
        test_id: The tutor test ID
        status: New status ("pending", "running", "completed", "failed")
        redis_config: Redis connection configuration
        started_at: Optional ISO timestamp
        finished_at: Optional ISO timestamp

    Returns:
        True if updated successfully
    """
    import redis.asyncio as aioredis
    from computor_backend.services.tutor_test_state import (
        update_tutor_test_status,
        TutorTestStatus,
    )

    logger.info(f"Updating tutor test {test_id} status to {status}")

    try:
        # Create Redis client
        redis_client = aioredis.Redis(
            host=redis_config.get("host", "localhost"),
            port=redis_config.get("port", 6379),
            password=redis_config.get("password") or None,
            db=redis_config.get("db", 0),
            decode_responses=True,
        )

        try:
            started_dt = None
            finished_dt = None
            if started_at:
                started_dt = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
            if finished_at:
                finished_dt = datetime.fromisoformat(finished_at.replace('Z', '+00:00'))

            result = await update_tutor_test_status(
                redis_client=redis_client,
                test_id=test_id,
                status=TutorTestStatus(status),
                started_at=started_dt,
                finished_at=finished_dt,
            )

            return result

        finally:
            await redis_client.close()

    except Exception as e:
        logger.error(f"Failed to update tutor test status: {e}")
        raise ApplicationError(message=str(e))


@activity.defn(name="commit_tutor_test_results_activity")
async def commit_tutor_test_results_activity(
    test_id: str,
    test_results: Dict[str, Any],
    redis_config: Dict[str, Any],
) -> bool:
    """
    Commit tutor test results to Redis and MinIO.

    Args:
        test_id: The tutor test ID
        test_results: Test results dictionary
        redis_config: Redis connection configuration

    Returns:
        True if committed successfully
    """
    import redis.asyncio as aioredis
    from computor_backend.services.tutor_test_state import (
        store_tutor_test_result,
        TutorTestStatus,
    )
    from computor_backend.services.tutor_test_storage import (
        store_tutor_test_result as store_result_minio,
    )

    logger.info(f"Committing tutor test results for {test_id}")

    try:
        # Determine status based on results
        if test_results.get("error") or test_results.get("timeout"):
            status = TutorTestStatus.FAILED
        else:
            status = TutorTestStatus.COMPLETED

        # Store result in MinIO
        await store_result_minio(test_id, test_results)
        logger.info(f"Stored result.json in MinIO for {test_id}")

        # Store result in Redis
        redis_client = aioredis.Redis(
            host=redis_config.get("host", "localhost"),
            port=redis_config.get("port", 6379),
            password=redis_config.get("password") or None,
            db=redis_config.get("db", 0),
            decode_responses=True,
        )

        try:
            await store_tutor_test_result(
                redis_client=redis_client,
                test_id=test_id,
                result=test_results,
                status=status,
            )
            logger.info(f"Stored result in Redis for {test_id}, status: {status.value}")
            return True

        finally:
            await redis_client.close()

    except Exception as e:
        logger.error(f"Failed to commit tutor test results: {e}")
        raise ApplicationError(message=str(e))


@activity.defn(name="store_tutor_test_artifacts_activity")
async def store_tutor_test_artifacts_activity(
    test_id: str,
    artifacts_path: str,
) -> int:
    """
    Store test artifacts from local directory to MinIO.

    Args:
        test_id: The tutor test ID
        artifacts_path: Path to directory containing artifacts

    Returns:
        Number of artifacts stored
    """
    import zipfile
    from io import BytesIO
    from computor_backend.services.tutor_test_storage import (
        store_tutor_test_artifact,
    )

    logger.info(f"Storing artifacts for tutor test {test_id} from {artifacts_path}")

    if not os.path.exists(artifacts_path):
        logger.info(f"Artifacts path does not exist: {artifacts_path}")
        return 0

    files = os.listdir(artifacts_path)
    if not files:
        logger.info("No artifacts to store")
        return 0

    stored_count = 0

    for root, dirs, filenames in os.walk(artifacts_path):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            rel_path = os.path.relpath(file_path, artifacts_path)

            with open(file_path, 'rb') as f:
                file_data = f.read()

            await store_tutor_test_artifact(
                test_id=test_id,
                filename=rel_path,
                file_data=file_data,
            )
            stored_count += 1
            logger.debug(f"Stored artifact: {rel_path}")

    logger.info(f"Stored {stored_count} artifacts for tutor test {test_id}")
    return stored_count


@activity.defn(name="run_complete_tutor_test")
async def run_complete_tutor_test_activity(
    test_id: str,
    example_version_id: str,
    service_type_config: Dict[str, Any],
    test_config: Dict[str, Any],
    api_config: Dict[str, Any],
    redis_config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Run complete tutor test in a single activity.

    This ensures all operations happen on the same worker with proper caching.

    Steps:
    1. Update status to "running"
    2. Fetch and cache reference example with dependencies
    3. Fetch tutor input from MinIO
    4. Execute tests
    5. Store artifacts
    6. Commit results

    Args:
        test_id: The tutor test ID
        example_version_id: Reference example version UUID
        service_type_config: Service type configuration
        test_config: Test configuration (testing_service_slug, etc.)
        api_config: API connection configuration
        redis_config: Redis connection configuration

    Returns:
        Test results dictionary
    """
    logger.info(f"Starting complete tutor test for {test_id}")

    # Create temporary work directory
    with tempfile.TemporaryDirectory(prefix=f"tutor_test_{test_id}_") as work_dir:
        try:
            # Step 1: Update status to running
            await update_tutor_test_status_activity(
                test_id=test_id,
                status="running",
                redis_config=redis_config,
                started_at=datetime.now(timezone.utc).isoformat(),
            )

            # Step 2: Fetch reference example with dependencies (cached)
            logger.info(f"Fetching reference example version {example_version_id}")
            reference_data = await fetch_example_version_with_dependencies(
                example_version_id=example_version_id,
                api_config=api_config,
                target_base_dir=EXAMPLE_CACHE_DIR,
            )

            reference_path = reference_data["main_path"]
            logger.info(f"Reference example at: {reference_path}")

            # Step 3: Fetch tutor input from MinIO
            tutor_dir = os.path.join(work_dir, "tutor")
            logger.info(f"Fetching tutor input for test {test_id}")
            tutor_data = await fetch_tutor_test_input(
                test_id=test_id,
                target_dir=tutor_dir,
            )

            tutor_path = tutor_data["tutor_path"]
            logger.info(f"Tutor input at: {tutor_path}")

            # Step 4: Execute tests
            logger.info("Executing tests")
            store_graphics_artifacts = test_config.get("store_graphics_artifacts", True)
            test_results = await execute_tests_activity(
                reference_path=reference_path,
                student_path=tutor_path,  # Tutor files act as "student" in test
                test_config=test_config,
                service_type_config=service_type_config,
                work_dir=work_dir,
                store_graphics_artifacts=store_graphics_artifacts,
            )

            logger.info(f"Test execution completed: {test_results}")

            # Step 5: Store artifacts
            artifacts_path = os.path.join(work_dir, "artifacts")
            if os.path.exists(artifacts_path) and os.listdir(artifacts_path):
                logger.info(f"Storing artifacts from {artifacts_path}")
                await store_tutor_test_artifacts_activity(test_id, artifacts_path)
            else:
                logger.info("No artifacts generated during test execution")

            # Step 6: Commit results
            logger.info("Committing results")
            await commit_tutor_test_results_activity(
                test_id=test_id,
                test_results=test_results,
                redis_config=redis_config,
            )

            return test_results

        except Exception as e:
            logger.error(f"Complete tutor test failed: {e}")

            # Try to update status to failed
            try:
                error_result = {
                    "passed": 0,
                    "failed": 1,
                    "total": 1,
                    "error": str(e),
                    "result_value": 0.0,
                }
                await commit_tutor_test_results_activity(
                    test_id=test_id,
                    test_results=error_result,
                    redis_config=redis_config,
                )
            except Exception as commit_error:
                logger.error(f"Failed to commit error result: {commit_error}")

            raise ApplicationError(message=str(e))


# ============================================================================
# Workflow
# ============================================================================

@register_task
@workflow.defn(name="tutor_testing", sandboxed=False)
class TutorTestingWorkflow(BaseWorkflow):
    """Execute tutor testing workflow - ephemeral, no database records."""

    @classmethod
    def get_name(cls) -> str:
        return "tutor_testing"

    @classmethod
    def get_execution_timeout(cls) -> timedelta:
        return timedelta(minutes=30)

    @workflow.run
    async def run(self, parameters: Dict[str, Any]) -> WorkflowResult:
        """
        Execute tutor testing workflow.

        Args:
            parameters: Dict containing:
                - test_id: Unique test identifier (UUID)
                - example_version_id: Reference example version UUID
                - service_type_config: Service type configuration
                - test_config: Test configuration
                - api_config: API connection configuration
                - redis_config: Redis connection configuration

        Returns:
            WorkflowResult with test results
        """
        test_id = parameters.get("test_id")
        example_version_id = parameters.get("example_version_id")
        service_type_config = parameters.get("service_type_config", {})
        test_config = parameters.get("test_config", {})
        api_config = parameters.get("api_config", {})
        redis_config = parameters.get("redis_config", {})

        workflow.logger.info(f"[TUTOR TEST START] test_id={test_id}")
        workflow.logger.info(
            f"[TUTOR TEST CONFIG] service_slug={test_config.get('testing_service_slug')}, "
            f"example_version_id={example_version_id}"
        )
        started_at = datetime.utcnow()

        try:
            # Run complete test in single activity
            workflow.logger.info(f"[ACTIVITY START] run_complete_tutor_test for test_id={test_id}")
            test_results = await workflow.execute_activity(
                run_complete_tutor_test_activity,
                args=[
                    test_id,
                    example_version_id,
                    service_type_config,
                    test_config,
                    api_config,
                    redis_config,
                ],
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=RetryPolicy(maximum_attempts=1),
            )

            completed_at = datetime.utcnow()
            duration = (completed_at - started_at).total_seconds()

            # Extract results
            if "summary" in test_results:
                passed = test_results["summary"]["passed"]
                failed = test_results["summary"]["failed"]
                total = test_results["summary"]["total"]
            else:
                passed = test_results.get("passed", 0)
                failed = test_results.get("failed", 0)
                total = test_results.get("total", 0)

            workflow.logger.info(
                f"[TUTOR TEST COMPLETE] test_id={test_id}, "
                f"passed={passed}/{total}, duration={duration:.1f}s"
            )

            return WorkflowResult(
                status="completed",
                result={
                    "test_id": test_id,
                    "started_at": started_at.isoformat(),
                    "completed_at": completed_at.isoformat(),
                    "duration_seconds": duration,
                },
                metadata={
                    "workflow_type": "tutor_testing",
                    "passed": passed,
                    "failed": failed,
                    "total": total,
                },
            )

        except Exception as e:
            workflow.logger.error(f"[TUTOR TEST FAILED] test_id={test_id}, error={str(e)}")
            return WorkflowResult(
                status="failed",
                result=None,
                error=str(e),
                metadata={
                    "workflow_type": "tutor_testing",
                    "test_id": test_id,
                },
            )
