"""
Student testing workflows and activities for Temporal.

This module handles testing of student submissions against reference examples.
Key improvements over deprecated version:
- Uses ExampleVersion from database instead of git repositories
- Caches reference examples to avoid repeated downloads
- Properly handles dependencies for both reference and student submissions
- Downloads from MinIO storage instead of cloning git repositories
"""

import os
import json
import tempfile
import subprocess
import asyncio
import uuid
import shutil
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from temporalio import workflow, activity
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

from .temporal_base import BaseWorkflow, WorkflowResult
from .registry import register_task
from computor_types.tasks import TaskStatus, map_task_status_to_int
from computor_types.results import ResultUpdate
from computor_client import ComputorClient
from computor_backend.utils.docker_utils import transform_localhost_url

logger = logging.getLogger(__name__)

# Cache directory for examples (persist across test runs)
# Student submissions are not cached - they use temporary directories
EXAMPLE_CACHE_DIR = os.environ.get("EXAMPLE_CACHE_DIR", "/tmp/examples")


# ============================================================================
# Storage and Caching Activities
# ============================================================================

def _save_example_files(target_path: str, files: Dict[str, Any]) -> None:
    """
    Save example files to disk, handling base64-encoded content.

    Args:
        target_path: Directory to save files to
        files: Dict of filename -> content
    """
    import base64

    os.makedirs(target_path, exist_ok=True)

    for filename, content in files.items():
        file_path = os.path.join(target_path, filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        if isinstance(content, dict) and "base64" in content:
            file_content = base64.b64decode(content["base64"])
            with open(file_path, 'wb') as f:
                f.write(file_content)
        elif isinstance(content, str):
            if content.startswith('data:') and ';base64,' in content:
                base64_data = content.split(';base64,', 1)[1]
                file_content = base64.b64decode(base64_data)
                with open(file_path, 'wb') as f:
                    f.write(file_content)
            else:
                with open(file_path, 'w') as f:
                    f.write(content)
        else:
            with open(file_path, 'wb') as f:
                f.write(content)


@activity.defn(name="fetch_example_version_with_dependencies")
async def fetch_example_version_with_dependencies(
    example_version_id: str,
    api_config: Dict[str, Any],
    target_base_dir: str,
) -> Dict[str, Any]:
    """
    Fetch an example version and all its dependencies from the API/MinIO.

    Uses local caching to avoid re-downloading the same example version.
    Each example_version is cached under its own version_id directory.

    Cache structure:
        /tmp/examples/{version_id}/         <- main example files
        /tmp/examples/{dep1_version_id}/    <- dependency 1 files
        /tmp/examples/{dep2_version_id}/    <- dependency 2 files

    Args:
        example_version_id: UUID of the ExampleVersion to fetch
        api_config: API connection configuration (requires 'token' and 'url')
        target_base_dir: Base directory for caching (e.g., /tmp/examples)

    Returns:
        Dict with:
            - main_path: Path to the main example
            - dependencies: List of dicts with dep info and paths
    """
    logger.info(f"Fetching example version {example_version_id}")

    # Cache path: /tmp/examples/{example_version_id}/
    cache_path = os.path.join(target_base_dir, example_version_id)

    # Check if already cached (directory exists with files)
    if os.path.isdir(cache_path) and os.listdir(cache_path):
        logger.info(f"Example version {example_version_id} found in cache at {cache_path}")
        # We still need to fetch dependency info from API to know their paths
        # But we can skip downloading files that are already cached

    # Fetch from API (needed for dependency resolution even if main is cached)
    base_url = transform_localhost_url(api_config.get("url", "http://localhost:8000"))
    api_token = api_config.get("token")
    if not api_token:
        raise ApplicationError("API token is required but not provided in api_config")

    async with ComputorClient(base_url=base_url, headers={"X-API-Token": api_token}) as client:

        # Download example version with dependencies
        logger.info(f"Downloading example version {example_version_id} with dependencies")
        response = await client._http.get(
            f"/examples/download/{example_version_id}?with_dependencies=true"
        )

        if response.status_code != 200:
            raise ApplicationError(
                f"Failed to download example version {example_version_id}: "
                f"{response.status_code} - {response.text}"
            )

        download_data = response.json()
        main_identifier = download_data.get("identifier") or download_data.get("directory")

        # Cache main example if not already cached
        if not os.path.isdir(cache_path) or not os.listdir(cache_path):
            logger.info(f"Caching main example {example_version_id} at {cache_path}")
            _save_example_files(cache_path, download_data.get("files", {}))
        else:
            logger.info(f"Main example {example_version_id} already cached")

        # Process dependencies - each cached under its own version_id
        dependencies_info = []
        for dep in download_data.get("dependencies", []):
            dep_version_id = dep.get("version_id")
            dep_identifier = dep.get("identifier") or dep.get("directory")
            dep_cache_path = os.path.join(target_base_dir, dep_version_id)

            # Cache dependency if not already cached
            if not os.path.isdir(dep_cache_path) or not os.listdir(dep_cache_path):
                logger.info(f"Caching dependency {dep_identifier} ({dep_version_id}) at {dep_cache_path}")
                _save_example_files(dep_cache_path, dep.get("files", {}))
            else:
                logger.info(f"Dependency {dep_identifier} ({dep_version_id}) already cached")

            dependencies_info.append({
                "example_id": dep.get("example_id"),
                "version_id": dep_version_id,
                "identifier": dep_identifier,
                "path": dep_cache_path,
            })

        logger.info(f"Cached example version {example_version_id}: main at {cache_path}, "
                   f"dependencies: {[d['identifier'] for d in dependencies_info]}")

        return {
            "main_path": cache_path,
            "main_identifier": main_identifier,
            "dependencies": dependencies_info,
            "example_version_id": example_version_id,
        }


@activity.defn(name="fetch_submission_artifact")
async def fetch_submission_artifact(
    artifact_id: str,
    api_config: Dict[str, Any],
    target_dir: str,
) -> Dict[str, Any]:
    """
    Fetch a submission artifact from MinIO storage.

    Args:
        artifact_id: UUID of the SubmissionArtifact
        api_config: API connection configuration (requires 'token' and 'url')
        target_dir: Directory to extract submission files

    Returns:
        Dict with:
            - submission_path: Path to extracted submission
            - artifact_id: Submission artifact ID
            - version_identifier: Git commit or version tag
    """
    logger.info(f"Fetching submission artifact {artifact_id}")

    base_url = transform_localhost_url(api_config.get("url", "http://localhost:8000"))
    api_token = api_config.get("token")
    if not api_token:
        raise ApplicationError("API token is required but not provided in api_config")

    async with ComputorClient(base_url=base_url, headers={"X-API-Token": api_token}) as client:

        # Download artifact as ZIP
        logger.info(f"Downloading submission artifact {artifact_id}")
        response = await client._http.get(
            f"/submissions/artifacts/{artifact_id}/download"
        )

        if response.status_code != 200:
            raise ApplicationError(
                f"Failed to download submission artifact {artifact_id}: "
                f"{response.status_code} - {response.text}"
            )

        # Save and extract ZIP
        import zipfile
        import io

        zip_data = io.BytesIO(response.content)
        os.makedirs(target_dir, exist_ok=True)

        with zipfile.ZipFile(zip_data, 'r') as zip_file:
            zip_file.extractall(target_dir)

        logger.info(f"Extracted submission to {target_dir}")

        # Check if ZIP contained a single top-level directory
        # (like old git clone structure: student-repo/example1/solution.py)
        extracted_items = os.listdir(target_dir)
        actual_submission_path = target_dir

        if len(extracted_items) == 1 and os.path.isdir(os.path.join(target_dir, extracted_items[0])):
            # ZIP had a single directory - use that as the submission path
            # This matches the old git clone behavior where we'd use student-repo/example1/
            actual_submission_path = os.path.join(target_dir, extracted_items[0])
            logger.info(f"ZIP contained single directory '{extracted_items[0]}', using as submission path")
        else:
            # ZIP had multiple files/dirs at root - use extraction dir
            logger.info(f"ZIP contained {len(extracted_items)} items at root, using extraction dir")

        logger.info(f"Final submission path: {actual_submission_path}")
        logger.info(f"  Contents: {os.listdir(actual_submission_path)}")

        # Get artifact metadata
        artifact_response = await client._http.get(
            f"/submissions/artifacts/{artifact_id}"
        )

        if artifact_response.status_code != 200:
            logger.warning(f"Could not fetch artifact metadata: {artifact_response.status_code}")
            artifact_data = {}
        else:
            artifact_data = artifact_response.json()

        return {
            "submission_path": actual_submission_path,
            "artifact_id": artifact_id,
            "version_identifier": artifact_data.get("version_identifier"),
            "properties": artifact_data.get("properties", {}),
        }


@activity.defn(name="execute_tests_with_backend")
async def execute_tests_activity(
    reference_path: str,
    student_path: str,
    test_config: Dict[str, Any],
    service_config: Dict[str, Any],
    service_type_config: Dict[str, Any],
    work_dir: Optional[str] = None,
    store_graphics_artifacts: bool = True,
) -> Dict[str, Any]:
    """
    Execute tests comparing student and reference implementations.

    Args:
        reference_path: Path to reference example (from cache)
        student_path: Path to student submission
        test_config: Test configuration
        service_config: Service instance configuration (from Service.config)
        service_type_config: Service type configuration (from ServiceType.properties)
        work_dir: Working directory for test execution (creates temp if not provided)
        store_graphics_artifacts: Whether to store graphics artifacts (plots, figures) generated during testing

    Returns:
        Test results dictionary
    """
    import logging
    import yaml

    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

    # Import the testing backend system
    from computor_backend.testing import execute_tests_with_backend

    # Extract service slug
    service_slug = test_config.get("testing_service_slug")

    # Use provided work_dir or create a temporary one
    # NOTE: work_dir should be the directory containing student_path
    if work_dir is None:
        # Extract work_dir from student_path (parent directory)
        work_dir = os.path.dirname(student_path)
    artifacts_path = os.path.join(work_dir, "artifacts")
    test_files_path = os.path.join(work_dir, "test_files")
    output_path = os.path.join(work_dir, "output")

    os.makedirs(artifacts_path, exist_ok=True)
    os.makedirs(test_files_path, exist_ok=True)
    os.makedirs(output_path, exist_ok=True)

    # Constants
    TEST_FILE_NAME = "test.yaml"
    SPEC_FILE_NAME = "specification.yaml"
    REPORT_FILE_NAME = "testSummary.json"

    # Create spec file
    spec_file_path = os.path.join(work_dir, SPEC_FILE_NAME)
    specfile_json = {
        "executionDirectory": student_path,
        "studentDirectory": student_path,
        "referenceDirectory": reference_path,
        "outputDirectory": output_path,
        "testDirectory": test_files_path,
        "artifactDirectory": artifacts_path,
        "studentTestCounter": 2,
        "storeGraphicsArtifacts": store_graphics_artifacts,
    }

    with open(spec_file_path, 'w') as yaml_file:
        yaml.dump(specfile_json, yaml_file)

    logger.info(f"Created specification file: {spec_file_path}")
    logger.info(f"Specification: {json.dumps(specfile_json, indent=2)}")

    # Debug: Log what files exist in each directory
    logger.info(f"=== DEBUG: Directory contents ===")
    logger.info(f"Reference path: {reference_path}")
    if os.path.exists(reference_path):
        logger.info(f"  Files: {os.listdir(reference_path)}")
    else:
        logger.error(f"  ERROR: Directory does not exist!")

    logger.info(f"Student path: {student_path}")
    if os.path.exists(student_path):
        logger.info(f"  Files: {os.listdir(student_path)}")
    else:
        logger.error(f"  ERROR: Directory does not exist!")

    logger.info(f"Work dir: {work_dir}")
    logger.info(f"  Files: {os.listdir(work_dir)}")
    logger.info(f"=== END DEBUG ===")

    # Read meta.yaml from reference if it exists
    meta_info = {}
    meta_filepath = os.path.join(reference_path, "meta.yaml")
    if os.path.exists(meta_filepath):
        try:
            with open(meta_filepath, "r") as meta_file:
                meta_info = yaml.safe_load(meta_file)
                logger.info(f"Loaded meta.yaml: {json.dumps(meta_info, indent=2)}")
        except Exception as e:
            logger.warning(f"Could not read meta.yaml: {e}")

    # Copy test files if specified
    mi_properties = meta_info.get("properties", {})
    mi_test_files = mi_properties.get("testFiles", [])
    if mi_test_files:
        for test_file in mi_test_files:
            try:
                src = os.path.join(reference_path, test_file)
                dst = os.path.join(test_files_path, test_file)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copyfile(src, dst)
                logger.info(f"Copied test file: {test_file}")
            except Exception as e:
                logger.warning(f"Could not copy test file {test_file}: {e}")

    # Test file is in reference directory
    test_file_path = os.path.join(reference_path, TEST_FILE_NAME)

    if not os.path.exists(test_file_path):
        raise ApplicationError(f"Test file not found: {test_file_path}")

    logger.info(f"Executing tests with service: {service_slug}")
    logger.info(f"Test file: {test_file_path}")
    logger.info(f"Spec file: {spec_file_path}")

    # Prepare job configuration
    job_config = {
        "user_id": test_config.get("user_id"),
        "course_member_id": test_config.get("course_member_id"),
        "course_content_id": test_config.get("course_content_id"),
        "testing_service_id": test_config.get("testing_service_id"),
        "student_path": student_path,
        "reference_path": reference_path,
    }

    # Execute tests
    try:
        backend_result = await execute_tests_with_backend(
            service_slug=service_slug,
            test_file_path=test_file_path,
            spec_file_path=spec_file_path,
            test_job_config=job_config,
            service_config=service_config,
            service_type_config=service_type_config,
        )

        # Check if backend returned an error/timeout directly
        # This happens for MATLAB timeout, communication errors, etc.
        if backend_result is not None and (backend_result.get("error") or backend_result.get("timeout")):
            logger.info(f"Backend returned error/timeout result: {backend_result}")
            test_results = backend_result
        else:
            # Read results from output file (normal case - results written to file)
            report_file_path = os.path.join(output_path, REPORT_FILE_NAME)
            if os.path.exists(report_file_path):
                logger.info(f"Reading results from file: {report_file_path}")
                with open(report_file_path, "r") as report_file:
                    test_results = json.load(report_file)
                logger.info(f"Test results: {json.dumps(test_results, indent=2)}")
            else:
                test_results = {
                    "passed": 0,
                    "failed": 1,
                    "total": 1,
                    "error": "No test results file found",
                }

        # Calculate result value
        try:
            if "summary" in test_results:
                result_value = test_results["summary"]["passed"] / test_results["summary"]["total"]
            else:
                result_value = test_results.get("passed", 0) / max(test_results.get("total", 1), 1)
            test_results["result_value"] = result_value
        except Exception as e:
            logger.warning(f"Could not calculate result value: {e}")
            test_results["result_value"] = 0.0

        return test_results

    except Exception as e:
        logger.error(f"Error executing tests: {e}")
        return {
            "passed": 0,
            "failed": 1,
            "total": 1,
            "error": str(e),
            "details": {"exception": str(e)},
            "result_value": 0.0,
        }


@activity.defn(name="commit_test_results")
async def commit_test_results_activity(
    result_id: str,
    test_results: Dict[str, Any],
    api_config: Dict[str, Any],
) -> bool:
    """
    Commit test results to the API.

    Args:
        result_id: UUID of the Result record
        test_results: Test results dictionary
        api_config: API connection configuration (requires 'token' and 'url')

    Returns:
        True if successful
    """
    logger.info(f"Committing test results for result {result_id}")

    try:
        base_url = transform_localhost_url(api_config.get("url", "http://localhost:8000"))
        api_token = api_config.get("token")
        if not api_token:
            raise ApplicationError("API token is required but not provided in api_config")

        async with ComputorClient(base_url=base_url, headers={"X-API-Token": api_token}) as client:

            # Determine status based on test results
            # Use FAILED status if there was an error or timeout
            if test_results.get("error") or test_results.get("timeout"):
                status = TaskStatus.FAILED
            else:
                status = TaskStatus.FINISHED

            # Update result
            result_update = ResultUpdate(
                status=status,
                result=test_results.get("result_value", 0.0),
                result_json=test_results,
            )

            response = await client.results.update(result_id, result_update)
            logger.info(f"Successfully updated result {result_id}")

            return True

    except Exception as e:
        logger.error(f"Failed to commit test results: {e}")
        raise ApplicationError(message=str(e))


async def store_test_artifacts(
    result_id: str,
    artifacts_path: str,
    api_config: Dict[str, Any],
) -> int:
    """
    Store all artifacts via the API by uploading them as a ZIP.

    This uploads artifacts through the backend API endpoint, removing the need
    for direct MinIO access from testing workers.

    Args:
        result_id: The result ID to associate artifacts with
        artifacts_path: Path to the directory containing artifact files
        api_config: API connection configuration (requires 'token' and 'url')

    Returns:
        Number of artifacts stored
    """
    import zipfile
    from io import BytesIO

    base_url = transform_localhost_url(api_config.get("url", "http://localhost:8000"))
    api_token = api_config.get("token")

    if not api_token:
        raise ApplicationError("API token is required for artifact upload")

    # Create ZIP in memory
    zip_buffer = BytesIO()
    file_count = 0

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(artifacts_path):
            for filename in files:
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, artifacts_path)
                zip_file.write(file_path, rel_path)
                file_count += 1
                logger.info(f"Added artifact '{rel_path}' to ZIP")

    if file_count == 0:
        logger.info("No artifacts to upload")
        return 0

    zip_buffer.seek(0)
    zip_data = zip_buffer.read()

    logger.info(f"Uploading {file_count} artifacts as ZIP ({len(zip_data)} bytes)")

    # Upload via API
    async with ComputorClient(base_url=base_url, headers={"X-API-Token": api_token}) as client:
        response = await client._http.post(
            f"/results/{result_id}/artifacts/upload",
            files={"file": ("artifacts.zip", zip_data, "application/zip")},
        )
        response.raise_for_status()

    logger.info(f"Uploaded {file_count} artifacts via API for result {result_id}")
    return file_count


@activity.defn(name="run_complete_student_test")
async def run_complete_student_test_activity(
    test_job: Dict[str, Any],
    service_config: Dict[str, Any],
    service_type_config: Dict[str, Any],
    result_id: str,
    api_config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Run complete student test in a single activity.

    This ensures all operations happen on the same worker with proper caching.

    Steps:
    1. Fetch and cache reference example with dependencies
    2. Fetch student submission artifact
    3. Execute tests
    4. Commit results

    Returns:
        Test results dictionary
    """
    logger.info(f"Starting complete student test for result {result_id}")

    # Create temporary work directory for this test run
    # Use TemporaryDirectory for automatic cleanup - submissions don't need to be cached
    with tempfile.TemporaryDirectory(prefix=f"test_{result_id}_") as work_dir:
        try:
            # Step 1: Fetch reference example with dependencies (cached)
            example_version_id = test_job.get("example_version_id")
            if not example_version_id:
                raise ApplicationError("Missing example_version_id in test_job")

            logger.info(f"Fetching reference example version {example_version_id}")
            reference_data = await fetch_example_version_with_dependencies(
                example_version_id=example_version_id,
                api_config=api_config,
                target_base_dir=EXAMPLE_CACHE_DIR,
            )

            reference_path = reference_data["main_path"]
            logger.info(f"Reference example at: {reference_path}")

            # Step 2: Fetch student submission
            artifact_id = test_job.get("artifact_id")
            if not artifact_id:
                raise ApplicationError("Missing artifact_id in test_job")

            student_dir = os.path.join(work_dir, "student")
            logger.info(f"Fetching student submission {artifact_id}")
            submission_data = await fetch_submission_artifact(
                artifact_id=artifact_id,
                api_config=api_config,
                target_dir=student_dir,
            )

            student_path = submission_data["submission_path"]
            logger.info(f"Student submission at: {student_path}")

            # Step 2.5: Copy dependencies next to student submission
            # This allows sys.path.append("../dep_identifier/") to work from student code
            dependencies = reference_data.get("dependencies", [])
            if dependencies:
                student_parent = os.path.dirname(student_path)
                for dep in dependencies:
                    dep_identifier = dep.get("identifier")
                    dep_source = dep.get("path")
                    if dep_identifier and dep_source and os.path.exists(dep_source):
                        dep_dest = os.path.join(student_parent, dep_identifier)
                        if not os.path.exists(dep_dest):
                            shutil.copytree(dep_source, dep_dest)
                            logger.info(f"Copied dependency: {dep_source} -> {dep_dest}")

            # Step 3: Execute tests
            logger.info("Executing tests")
            # Get store_graphics_artifacts from test_job (default: True)
            store_graphics_artifacts = test_job.get("store_graphics_artifacts", True)
            test_results = await execute_tests_activity(
                reference_path=reference_path,
                student_path=student_path,
                test_config=test_job,
                service_config=service_config,
                service_type_config=service_type_config,
                work_dir=work_dir,  # Pass the temporary work directory
                store_graphics_artifacts=store_graphics_artifacts,
            )

            logger.info(f"Test execution completed: {test_results}")

            # Step 3.5: Store any generated artifacts via API
            # This allows testing workers to operate without direct MinIO access
            artifacts_path = os.path.join(work_dir, "artifacts")
            if os.path.exists(artifacts_path) and os.listdir(artifacts_path):
                logger.info(f"Found artifacts to store in {artifacts_path}")
                await store_test_artifacts(result_id, artifacts_path, api_config)
            else:
                logger.info("No artifacts generated during test execution")

            # Step 4: Commit results
            logger.info("Committing results to API")
            await commit_test_results_activity(result_id, test_results, api_config)

            return test_results

        except Exception as e:
            logger.error(f"Complete student test failed: {e}")

            # Try to update result status to FAILED
            try:
                await commit_test_results_activity(
                    result_id,
                    {
                        "passed": 0,
                        "failed": 1,
                        "total": 1,
                        "error": str(e),
                        "result_value": 0.0,
                    },
                    api_config,
                )
            except:
                pass  # Best effort

            raise ApplicationError(message=str(e))


# ============================================================================
# Workflow
# ============================================================================

@register_task
@workflow.defn(name="student_testing", sandboxed=False)
class StudentTestingWorkflow(BaseWorkflow):
    """Execute student testing workflow with example caching."""

    @classmethod
    def get_name(cls) -> str:
        return "student_testing"

    @classmethod
    def get_execution_timeout(cls) -> timedelta:
        return timedelta(minutes=30)

    @workflow.run
    async def run(self, parameters: Dict[str, Any]) -> WorkflowResult:
        """
        Execute student testing workflow.

        Args:
            parameters: Dict containing:
                - test_job: Test job configuration
                - service_config: Service instance configuration
                - service_type_config: Service type configuration
                - result_id: Database result ID

        Returns:
            WorkflowResult with test results
        """
        test_job = parameters.get("test_job", {})
        service_config = parameters.get("service_config", {})
        service_type_config = parameters.get("service_type_config", {})
        result_id = parameters.get("result_id")

        job_id = str(uuid.uuid4())
        workflow.logger.info(f"[TEST START] job={job_id}, result_id={result_id}")
        workflow.logger.info(f"[TEST CONFIG] service_slug={test_job.get('testing_service_slug')}, "
                            f"artifact_id={test_job.get('artifact_id')}, "
                            f"example_version_id={test_job.get('example_version_id')}")
        started_at = datetime.utcnow()

        try:
            # API configuration
            api_url = os.environ.get("API_URL", "http://localhost:8000")
            api_token = os.environ.get("API_TOKEN")
            api_config = {
                "url": api_url,
                "token": api_token,
            }
            workflow.logger.info(f"[API CONFIG] url={api_url}, token_present={bool(api_token)}")

            # Run complete test in single activity
            workflow.logger.info(f"[ACTIVITY START] run_complete_student_test for result_id={result_id}")
            test_results = await workflow.execute_activity(
                run_complete_student_test_activity,
                args=[test_job, service_config, service_type_config, result_id, api_config],
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

            workflow.logger.info(f"[TEST COMPLETE] result_id={result_id}, passed={passed}/{total}, duration={duration:.1f}s")

            return WorkflowResult(
                status="completed",
                result={
                    "test_job_id": job_id,
                    "started_at": started_at.isoformat(),
                    "completed_at": completed_at.isoformat(),
                    "duration_seconds": duration,
                },
                metadata={
                    "workflow_type": "student_testing",
                    "passed": passed,
                    "failed": failed,
                    "total": total,
                },
            )

        except Exception as e:
            workflow.logger.error(f"[TEST FAILED] result_id={result_id}, error={str(e)}")
            return WorkflowResult(
                status="failed",
                result=None,
                error=str(e),
                metadata={
                    "workflow_type": "student_testing",
                    "test_job_id": job_id,
                },
            )
