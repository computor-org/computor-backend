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
import shutil
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from temporalio import workflow, activity
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

from .temporal_base import (
    BaseWorkflow,
    WorkflowResult,
    extract_test_counts,
    start_activity_heartbeat,
)
from .registry import register_task
from computor_types.tasks import TaskStatus, map_task_status_to_int
from computor_types.results import ResultUpdate
from computor_client import ComputorClient
from computor_backend.utils.docker_utils import transform_localhost_url

from computor_backend.tasks.worker_settings import get_worker_settings

logger = logging.getLogger(__name__)


# ============================================================================
# Storage and Caching Activities
# ============================================================================

VERSION_MARKER_FILENAME = ".example_version_id"

# Retry budget for the terminal "write the Result row" PATCH. See
# commit_test_results_activity — losing this call loses the whole test run.
COMMIT_MAX_ATTEMPTS = 4
COMMIT_RETRY_BASE_DELAY = 2.0  # seconds; doubled per attempt

# How long one test run may actually execute for, once a worker has picked it up.
TEST_ACTIVITY_TIMEOUT = timedelta(minutes=30)

# A heartbeat is emitted every ACTIVITY_HEARTBEAT_INTERVAL_SECONDS (30s); miss
# several in a row and the worker is presumed dead.
TEST_ACTIVITY_HEARTBEAT_TIMEOUT = timedelta(minutes=2)

# Whole-workflow budget, which also covers waiting in the queue. Deliberately
# much larger than TEST_ACTIVITY_TIMEOUT so a backlog delays a test rather than
# failing it — see StudentTestingWorkflow.get_execution_timeout.
TEST_WORKFLOW_EXECUTION_TIMEOUT = timedelta(hours=4)


def _resolve_within(base_dir: str, filename: str) -> str:
    """Resolve ``filename`` under ``base_dir``, refusing to escape it.

    Filenames come from the API payload of an uploaded example, i.e. from
    whoever authored that example. A plain ``os.path.join`` happily accepts
    ``../../.ssh/authorized_keys`` or an absolute path and writes outside the
    cache — into the worker's own home. Anchor every write instead.
    """
    base = os.path.realpath(base_dir)
    candidate = os.path.realpath(os.path.join(base, filename))
    if candidate != base and not candidate.startswith(base + os.sep):
        raise ApplicationError(
            f"Refusing to write example file outside its directory: {filename!r}"
        )
    return candidate


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
        file_path = _resolve_within(target_path, filename)
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


def _cached_version_matches(cache_path: str, expected_version_id: str) -> bool:
    """Return True if cache_path is non-empty and its version marker matches.

    A missing marker is treated as a stale cache so legacy directories get
    rewritten with the current version_id.
    """
    if not os.path.isdir(cache_path) or not os.listdir(cache_path):
        return False
    marker_path = os.path.join(cache_path, VERSION_MARKER_FILENAME)
    if not os.path.isfile(marker_path):
        return False
    try:
        with open(marker_path, "r") as f:
            return f.read().strip() == str(expected_version_id)
    except OSError:
        return False


def _cache_example(
    cache_path: str,
    version_id: str,
    files: Dict[str, Any],
) -> None:
    """Wipe `cache_path` and rewrite it with `files`, then stamp the version.

    Used to keep `/tmp/examples/<identifier>/` aligned with the requested
    version — no stale content from an older example_version sticks around.
    """
    if os.path.isdir(cache_path):
        shutil.rmtree(cache_path)
    _save_example_files(cache_path, files)
    with open(os.path.join(cache_path, VERSION_MARKER_FILENAME), "w") as f:
        f.write(str(version_id))


@activity.defn(name="fetch_example_version_with_dependencies")
async def fetch_example_version_with_dependencies(
    example_version_id: str,
    api_config: Dict[str, Any],
    target_base_dir: str,
) -> Dict[str, Any]:
    """
    Fetch an example version and all its dependencies from the API/MinIO.

    Uses local caching to avoid re-downloading the same example version.
    Each example is cached under its identifier with a version_id marker so
    the testing engine can resolve sibling `../<identifier>/` imports while
    still being able to detect a stale cache and refetch on version change.

    Cache structure:
        /tmp/examples/{main_identifier}/    <- main example files
        /tmp/examples/{dep1_identifier}/    <- dependency 1 files
        /tmp/examples/{dep2_identifier}/    <- dependency 2 files
        Each directory contains a .example_version_id marker file.

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
        if not main_identifier:
            raise ApplicationError(
                f"Example version {example_version_id} response missing identifier"
            )

        # Cache main example by identifier, refetching when the version marker
        # does not match (or is missing on legacy cache entries).
        cache_path = os.path.join(target_base_dir, main_identifier)
        if _cached_version_matches(cache_path, example_version_id):
            logger.info(
                f"Main example {main_identifier} ({example_version_id}) already cached at {cache_path}"
            )
        else:
            logger.info(
                f"Caching main example {main_identifier} ({example_version_id}) at {cache_path}"
            )
            _cache_example(cache_path, example_version_id, download_data.get("files", {}))

        # Cache dependencies by identifier — same scheme as the main example —
        # so the reference run can resolve sibling `../<dep_identifier>/`
        # imports out of the examples cache.
        dependencies_info = []
        for dep in download_data.get("dependencies", []):
            dep_version_id = dep.get("version_id")
            dep_identifier = dep.get("identifier") or dep.get("directory")
            if not dep_identifier:
                logger.warning(f"Skipping dependency without identifier: {dep_version_id}")
                continue

            dep_cache_path = os.path.join(target_base_dir, dep_identifier)

            if _cached_version_matches(dep_cache_path, dep_version_id):
                logger.info(
                    f"Dependency {dep_identifier} ({dep_version_id}) already cached"
                )
            else:
                logger.info(
                    f"Caching dependency {dep_identifier} ({dep_version_id}) at {dep_cache_path}"
                )
                _cache_example(dep_cache_path, dep_version_id, dep.get("files", {}))

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
def execute_tests_activity(
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

    BLOCKING activity: runs the test backend, whose work is a synchronous
    ``subprocess.run`` (up to 5 min) plus local file I/O. A plain ``def`` — the
    orchestrators (run_complete_student_test / run_tutor_test) invoke it via
    ``asyncio.to_thread`` so the subprocess never stalls the event loop, and if
    Temporal ever dispatched it directly it would run in the worker thread pool.
    The backend helper is async-by-convention (no real awaits), so it is driven
    with ``asyncio.run`` here (no running loop in this thread).

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

    # Execute tests. execute_tests_with_backend is async-by-convention (its work
    # is a blocking subprocess); this activity is sync, so drive it with
    # asyncio.run in the current thread.
    try:
        backend_result = asyncio.run(execute_tests_with_backend(
            service_slug=service_slug,
            test_file_path=test_file_path,
            spec_file_path=spec_file_path,
            test_job_config=job_config,
            service_config=service_config,
            service_type_config=service_type_config,
        ))

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
            p, _, t = extract_test_counts(test_results)
            test_results["result_value"] = p / max(t, 1)
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

    base_url = transform_localhost_url(api_config.get("url", "http://localhost:8000"))
    api_token = api_config.get("token")
    if not api_token:
        raise ApplicationError("API token is required but not provided in api_config")

    # Determine status based on test results
    # Use FAILED status if there was an error or timeout
    if test_results.get("error") or test_results.get("timeout"):
        status = TaskStatus.FAILED
    else:
        status = TaskStatus.FINISHED

    result_update = ResultUpdate(
        status=status,
        result=test_results.get("result_value", 0.0),
        result_json=test_results,
    )

    # This PATCH is the only place a finished run becomes visible: the Result
    # row is the source of truth and the worker holds no DB access. The client
    # has a short timeout and no retries of its own, so a single blip used to
    # throw away a completed test run. Retry with backoff before giving up.
    last_error: Optional[Exception] = None
    for attempt in range(1, COMMIT_MAX_ATTEMPTS + 1):
        try:
            async with ComputorClient(base_url=base_url, headers={"X-API-Token": api_token}) as client:
                await client.results.update(result_id, result_update)
            logger.info(f"Successfully updated result {result_id}")
            return True
        except Exception as e:
            last_error = e
            if attempt < COMMIT_MAX_ATTEMPTS:
                delay = COMMIT_RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    "Failed to commit test results for %s (attempt %d/%d), retrying in %.1fs: %s",
                    result_id, attempt, COMMIT_MAX_ATTEMPTS, delay, e,
                )
                await asyncio.sleep(delay)

    logger.error(f"Failed to commit test results after {COMMIT_MAX_ATTEMPTS} attempts: {last_error}")
    raise ApplicationError(message=str(last_error))


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
    from computor_backend.tasks.api_client import upload_artifacts_zip

    return await upload_artifacts_zip(
        api_config, f"/results/{result_id}/artifacts/upload", artifacts_path
    )


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

    # Env-first API config: the worker's env overrides the workflow-passed value.
    from computor_backend.tasks.api_client import resolve_api_config
    api_config = resolve_api_config(api_config)
    logger.info("[ACTIVITY API CONFIG] url=%s, token_present=%s", api_config["url"], bool(api_config["token"]))

    # Keep Temporal informed that this worker is alive for the whole
    # (potentially very long) run, so the heartbeat_timeout declared on the
    # activity detects a killed worker within minutes instead of waiting out
    # the 30 minute start_to_close.
    heartbeat = start_activity_heartbeat()

    # Create temporary work directory for this test run.
    # TemporaryDirectory cleans up automatically — submissions are not cached.
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
                target_base_dir=get_worker_settings().example_cache_dir,
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

            # Test dependencies are mirrored next to studentDirectory and
            # referenceDirectory by BaseTester._stage_test_dependencies, using
            # the identifier-aliased paths in the examples cache produced by
            # fetch_example_version_with_dependencies.

            # Step 3: Execute tests. execute_tests_activity is now a blocking
            # (sync) function; offload it to a thread so its subprocess does not
            # stall this orchestrator's event loop.
            logger.info("Executing tests")
            store_graphics_artifacts = test_job.get("store_graphics_artifacts", True)
            test_results = await asyncio.to_thread(
                execute_tests_activity,
                reference_path=reference_path,
                student_path=student_path,
                test_config=test_job,
                service_config=service_config,
                service_type_config=service_type_config,
                work_dir=work_dir,
                store_graphics_artifacts=store_graphics_artifacts,
            )

            logger.info(f"Test execution completed: {test_results}")

            # Step 3.5: Store any generated artifacts via API.
            #
            # Best-effort on purpose: the tests have already run and their
            # outcome is the thing that matters. Uploading figures is a large
            # multipart POST on a client with a short timeout, so letting it
            # throw here used to discard a *passing* run and commit
            # {passed: 0, failed: 1} instead. Losing a plot is acceptable;
            # losing the verdict is not.
            artifacts_path = os.path.join(work_dir, "artifacts")
            if os.path.exists(artifacts_path) and os.listdir(artifacts_path):
                logger.info(f"Found artifacts to store in {artifacts_path}")
                try:
                    await store_test_artifacts(result_id, artifacts_path, api_config)
                except Exception:
                    logger.warning(
                        "Failed to upload artifacts for result %s; committing test "
                        "results anyway", result_id, exc_info=True,
                    )
                    test_results["artifacts_upload_failed"] = True
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
            except Exception:
                # Best-effort failure-result POST; the original test failure is
                # what we ultimately surface to Temporal below.
                logger.warning("Failed to POST testing failure result", exc_info=True)

            raise ApplicationError(message=str(e))

        finally:
            heartbeat.cancel()


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
        """Budget for the whole workflow, INCLUDING time spent queued.

        This clock starts when the workflow is submitted, not when a worker
        picks it up. It used to equal the activity's own 30 minute execution
        budget, so during a deadline rush — when tests queue behind a
        single-concurrency MATLAB engine — a submission could time out before it
        ever ran, and the student saw a failed test for what was purely a
        capacity problem. The real per-run limit is the activity's
        start_to_close_timeout below; this only has to be generous enough to
        cover queue wait as well.
        """
        return TEST_WORKFLOW_EXECUTION_TIMEOUT

    @classmethod
    def get_retry_policy(cls) -> RetryPolicy:
        """A test run is executed exactly once.

        The base policy retries a failed workflow 3x. For testing that would
        re-execute a student's submission against the same ``result_id`` — the
        run is visible as failed and may be retried deliberately, never
        silently. Must stay at 1 now that ``run()`` propagates failures
        (see the comment there).
        """
        return RetryPolicy(maximum_attempts=1)

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

        job_id = str(workflow.uuid4())
        workflow.logger.info(f"[TEST START] job={job_id}, result_id={result_id}")
        workflow.logger.info(f"[TEST CONFIG] service_slug={test_job.get('testing_service_slug')}, "
                            f"artifact_id={test_job.get('artifact_id')}, "
                            f"example_version_id={test_job.get('example_version_id')}")
        started_at = datetime.utcnow()

        try:
            # API configuration - activities read from their own os.environ
            # (workflows must not access os.environ for Temporal determinism)
            api_config = {
                "url": "http://localhost:8000",
                "token": None,
            }

            # Run complete test in single activity
            workflow.logger.info(f"[ACTIVITY START] run_complete_student_test for result_id={result_id}")
            test_results = await workflow.execute_activity(
                run_complete_student_test_activity,
                args=[test_job, service_config, service_type_config, result_id, api_config],
                start_to_close_timeout=TEST_ACTIVITY_TIMEOUT,
                # The activity pumps activity.heartbeat() while it works, so a
                # worker that is SIGKILLed / OOM-killed is detected in ~2 min
                # instead of only when start_to_close expires 30 minutes later.
                heartbeat_timeout=TEST_ACTIVITY_HEARTBEAT_TIMEOUT,
                retry_policy=RetryPolicy(maximum_attempts=1),
            )

            completed_at = datetime.utcnow()
            duration = (completed_at - started_at).total_seconds()

            # Extract results
            passed, failed, total = extract_test_counts(test_results)

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
            # Propagate, never `return WorkflowResult(status="failed")`.
            #
            # Returning normally makes Temporal record the execution as
            # COMPLETED, and the API reconciler
            # (business_logic/testing_orchestration.sync_result_status_from_temporal)
            # maps COMPLETED -> FINISHED without ever reading this payload. A
            # crashed run therefore surfaced as a genuine "FINISHED, 0%" result
            # — and since FINISHED is not a retryable status, the partial unique
            # indexes on `result` then blocked every re-test of that version with
            # an IntegrityError. Raising marks the workflow FAILED, which the
            # reconciler maps to ResultStatus.FAILED (retryable).
            workflow.logger.error(f"[TEST FAILED] result_id={result_id}, error={str(e)}")
            raise


ACTIVITIES = [
    fetch_example_version_with_dependencies,
    fetch_submission_artifact,
    execute_tests_activity,
    commit_test_results_activity,
    run_complete_student_test_activity,
]
