"""
Tutor testing workflows and activities for Temporal.

This module handles testing of tutor-uploaded code against reference examples.
Unlike student testing, tutor tests:
- Don't create database records (state in Redis only, managed by API)
- Store files in 'tutor-tests' bucket (with lifecycle cleanup)
- Are ephemeral (TTL-based expiration)

IMPORTANT: Temporal does NOT interact with Redis. The API layer handles all
Redis state management. Temporal only runs tests and returns results.

Reuses activities from temporal_student_testing where possible.
"""

import os
import tempfile
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

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


@activity.defn(name="store_tutor_test_result_to_minio")
async def store_tutor_test_result_to_minio(
    test_id: str,
    test_results: Dict[str, Any],
) -> bool:
    """
    Store test results to MinIO (not Redis - that's handled by API).

    Args:
        test_id: The tutor test ID
        test_results: Test results dictionary

    Returns:
        True if stored successfully
    """
    from computor_backend.services.tutor_test_storage import (
        store_tutor_test_result as store_result_minio,
    )

    logger.info(f"Storing tutor test results to MinIO for {test_id}")

    try:
        await store_result_minio(test_id, test_results)
        logger.info(f"Stored result.json in MinIO for {test_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to store tutor test result to MinIO: {e}")
        raise ApplicationError(message=str(e))


@activity.defn(name="run_tutor_test_activity")
async def run_tutor_test_activity(
    test_id: str,
    example_version_id: str,
    service_type_config: Dict[str, Any],
    test_config: Dict[str, Any],
    api_config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Run tutor test and return results. Does NOT interact with Redis.

    Steps:
    1. Fetch and cache reference example with dependencies
    2. Fetch tutor input from MinIO
    3. Execute tests
    4. Store artifacts to MinIO
    5. Store result.json to MinIO
    6. Return results (API will write to Redis)

    Args:
        test_id: The tutor test ID
        example_version_id: Reference example version UUID
        service_type_config: Service type configuration
        test_config: Test configuration (testing_service_slug, etc.)
        api_config: API connection configuration

    Returns:
        Test results dictionary (API writes this to Redis)
    """
    logger.info(f"Starting tutor test for {test_id}")

    # Create temporary work directory
    with tempfile.TemporaryDirectory(prefix=f"tutor_test_{test_id}_") as work_dir:
        try:
            # Step 1: Fetch reference example with dependencies (cached)
            logger.info(f"Fetching reference example version {example_version_id}")
            reference_data = await fetch_example_version_with_dependencies(
                example_version_id=example_version_id,
                api_config=api_config,
                target_base_dir=EXAMPLE_CACHE_DIR,
            )

            reference_path = reference_data["main_path"]
            logger.info(f"Reference example at: {reference_path}")

            # Step 2: Fetch tutor input from MinIO
            tutor_dir = os.path.join(work_dir, "tutor")
            logger.info(f"Fetching tutor input for test {test_id}")
            tutor_data = await fetch_tutor_test_input(
                test_id=test_id,
                target_dir=tutor_dir,
            )

            tutor_path = tutor_data["tutor_path"]
            logger.info(f"Tutor input at: {tutor_path}")

            # Step 3: Execute tests
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

            # Step 4: Store artifacts to MinIO
            artifacts_path = os.path.join(work_dir, "artifacts")
            artifact_count = 0
            if os.path.exists(artifacts_path) and os.listdir(artifacts_path):
                logger.info(f"Storing artifacts from {artifacts_path}")
                artifact_count = await store_tutor_test_artifacts_activity(test_id, artifacts_path)
            else:
                logger.info("No artifacts generated during test execution")

            # Add artifact count to results
            test_results["artifact_count"] = artifact_count

            # Step 5: Store result.json to MinIO
            await store_tutor_test_result_to_minio(test_id, test_results)

            # Return results - API will write to Redis
            return test_results

        except Exception as e:
            logger.error(f"Tutor test failed: {e}")

            # Create error result
            error_result = {
                "passed": 0,
                "failed": 1,
                "total": 1,
                "error": str(e),
                "result_value": 0.0,
                "artifact_count": 0,
            }

            # Try to store error result to MinIO
            try:
                await store_tutor_test_result_to_minio(test_id, error_result)
            except Exception as store_error:
                logger.error(f"Failed to store error result to MinIO: {store_error}")

            raise ApplicationError(message=str(e))


# ============================================================================
# Workflow
# ============================================================================

@register_task
@workflow.defn(name="tutor_testing", sandboxed=False)
class TutorTestingWorkflow(BaseWorkflow):
    """
    Execute tutor testing workflow - ephemeral, no database records.

    IMPORTANT: This workflow does NOT interact with Redis.
    All Redis state management is handled by the API layer.
    The workflow returns results which the API writes to Redis.
    """

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

        Returns:
            WorkflowResult with test results (API writes to Redis)
        """
        test_id = parameters.get("test_id")
        example_version_id = parameters.get("example_version_id")
        service_type_config = parameters.get("service_type_config", {})
        test_config = parameters.get("test_config", {})

        workflow.logger.info(f"[TUTOR TEST START] test_id={test_id}")
        workflow.logger.info(
            f"[TUTOR TEST CONFIG] service_slug={test_config.get('testing_service_slug')}, "
            f"example_version_id={example_version_id}"
        )
        started_at = datetime.utcnow()

        try:
            # API configuration from environment (same pattern as StudentTestingWorkflow)
            api_url = os.environ.get("API_URL", "http://localhost:8000")
            api_token = os.environ.get("API_TOKEN")
            api_config = {
                "url": api_url,
                "token": api_token,
            }
            workflow.logger.info(f"[API CONFIG] url={api_url}, token_present={bool(api_token)}")

            # Run test activity
            workflow.logger.info(f"[ACTIVITY START] run_tutor_test_activity for test_id={test_id}")
            test_results = await workflow.execute_activity(
                run_tutor_test_activity,
                args=[
                    test_id,
                    example_version_id,
                    service_type_config,
                    test_config,
                    api_config,
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

            # Return results - API will write these to Redis
            return WorkflowResult(
                status="completed",
                result={
                    "test_id": test_id,
                    "test_results": test_results,  # Full test results for API to store
                    "started_at": started_at.isoformat(),
                    "completed_at": completed_at.isoformat(),
                    "duration_seconds": duration,
                },
                metadata={
                    "workflow_type": "tutor_testing",
                    "passed": passed,
                    "failed": failed,
                    "total": total,
                    "artifact_count": test_results.get("artifact_count", 0),
                },
            )

        except Exception as e:
            workflow.logger.error(f"[TUTOR TEST FAILED] test_id={test_id}, error={str(e)}")
            return WorkflowResult(
                status="failed",
                result={
                    "test_id": test_id,
                    "error": str(e),
                },
                error=str(e),
                metadata={
                    "workflow_type": "tutor_testing",
                    "test_id": test_id,
                },
            )
