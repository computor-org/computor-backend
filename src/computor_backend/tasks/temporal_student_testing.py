"""
Student testing workflows and activities for Temporal.
"""

import os
import json
import tempfile
import subprocess
import asyncio
import uuid
import shutil
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from temporalio import workflow, activity
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

from .temporal_base import BaseWorkflow, WorkflowResult
from .registry import register_task
from computor_types.tests import TestJob
from computor_types.repositories import Repository
from computor_types.results import ResultGet, ResultInterface, ResultQuery, ResultUpdate
from computor_types.tasks import TaskStatus, map_task_status_to_int
# TODO Phase 4: Update to use computor_client instead of old CrudClient
# from computor_backend.client.crud_client import CrudClient
from computor_backend.utils.docker_utils import transform_localhost_url


# Activities
@activity.defn(name="clone_repository")
async def clone_repository_activity(repo_data: Dict[str, Any], target_path: str) -> bool:
    """Clone a git repository to target path."""
    import logging
    logger = logging.getLogger(__name__)
    
    repo = Repository(**repo_data)
    
    # Transform localhost URLs for Docker environment
    original_url = repo.url
    transformed_url = transform_localhost_url(repo.url)
    
    if original_url != transformed_url:
        logger.info(f"Transformed URL from {original_url} to {transformed_url}")
    
    # Construct git clone command
    clone_cmd = ["git", "clone"]
    
    if repo.token:
        # Add token authentication to URL
        url_parts = transformed_url.split("://")
        if len(url_parts) == 2:
            clone_url = f"{url_parts[0]}://oauth2:{repo.token}@{url_parts[1]}"
        else:
            clone_url = transformed_url
    else:
        clone_url = transformed_url
    
    # Clean up target directory if it exists (for retry scenarios)
    if os.path.exists(target_path):
        logger.warning(f"Target path {target_path} already exists, removing it for retry")
        shutil.rmtree(target_path)
    
    clone_cmd.extend([clone_url, target_path])
    
    # Execute clone
    result = subprocess.run(clone_cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise Exception(f"Failed to clone repository: {result.stderr}")
    
    # Checkout specific commit if provided
    if repo.commit:
        checkout_cmd = ["git", "-C", target_path, "checkout", repo.commit]
        result = subprocess.run(checkout_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Failed to checkout commit {repo.commit}: {result.stderr}")
    
    return True


@activity.defn(name="execute_tests")
async def execute_tests_activity(
    student_path: str,
    reference_path: str,
    test_config: Dict[str, Any],
    backend_properties: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute tests comparing student and reference implementations."""
    
    import logging
    import yaml
    import json
    import shutil
    logger = logging.getLogger(__name__)

    logging.basicConfig(level=logging.INFO)
    
    # Import the testing backend system
    from computor_backend.testing import execute_tests_with_backend
    from computor_types.tests import TestJob
    
    # Parse the test job configuration
    test_job = TestJob(**test_config)
    
    # Determine backend type from properties or test job
    backend_type = test_config.get("execution_backend_type")
    
    # Create work directory structure within the temp directory
    work_dir = os.path.dirname(student_path)  # Get parent temp directory
    artifacts_path = os.path.join(work_dir, "artifacts")
    test_files_path = os.path.join(work_dir, "test_files")
    output_path = os.path.join(work_dir, "output")

    reference_path = os.path.join(reference_path,test_config["reference"]["path"])
    student_path = os.path.join(student_path,test_config["module"]["path"])
    
    # Constants from old system
    TEST_FILE_NAME = "test.yaml"
    SPEC_FILE_NAME = "specification.yaml"
    REPORT_FILE_NAME = "testSummary.json"
    
    # Create spec file with directory information
    spec_file_path = os.path.join(work_dir, SPEC_FILE_NAME)
    specfile_json = {
        "executionDirectory": student_path,
        "studentDirectory": student_path,
        "referenceDirectory": reference_path,
        "outputDirectory": output_path,
        "testDirectory": test_files_path,
        "artifactDirectory": artifacts_path,
        "studentTestCounter": 2,
    }
    
    with open(spec_file_path, 'w') as yaml_file:
        yaml.dump(specfile_json, yaml_file)
    
    logger.info(f"Created specification file: {spec_file_path}")
    logger.info(f"Specification: {json.dumps(specfile_json, indent=2)}")
    
    # Read meta.yaml from reference repository if it exists
    meta_info = {}
    meta_filepath = os.path.join(reference_path, "meta.yaml")
    if os.path.exists(meta_filepath):
        try:
            with open(meta_filepath, "r") as meta_file:
                meta_info = yaml.safe_load(meta_file)
                logger.info(f"Loaded meta.yaml: {json.dumps(meta_info, indent=2)}")
        except Exception as e:
            logger.warning(f"Could not read meta.yaml: {e}")
    
    # Copy test files if specified in meta.yaml
    mi_properties = meta_info.get("properties", {})
    mi_test_files = mi_properties.get("testFiles", [])
    if mi_test_files:
        os.makedirs(test_files_path, exist_ok=True)
        for test_file in mi_test_files:
            try:
                src = os.path.join(reference_path, test_file)
                dst = os.path.join(test_files_path, test_file)
                shutil.copyfile(src, dst)
                logger.info(f"Copied test file: {test_file}")
            except Exception as e:
                logger.warning(f"Could not copy test file {test_file}: {e}")
    
    # Test file path is always from reference repository
    test_file_path = os.path.join(reference_path, TEST_FILE_NAME)
    
    logger.info(f"Executing tests with backend: {backend_type}")
    logger.info(f"Test file: {test_file_path}")
    logger.info(f"Spec file: {spec_file_path}")
    
    # Prepare job configuration for the backend
    job_config = {
        "user_id": test_job.user_id,
        "course_member_id": test_job.course_member_id,
        "course_content_id": test_job.course_content_id,
        "execution_backend_id": test_job.execution_backend_id,
        "test_number": test_job.test_number,
        "submission_number": test_job.submission_number,
        "submit": test_config.get("submit", False),
        "student_path": student_path,
        "reference_path": reference_path
    }
    
    # Execute tests using the appropriate backend
    try:
        await execute_tests_with_backend(
            backend_type=backend_type,
            test_file_path=test_file_path,
            spec_file_path=spec_file_path,
            test_job_config=job_config,
            backend_properties=backend_properties
        )

        test_results = None
        
        # If no results returned, check for output file (some backends write to file)
        if test_results is None:
            report_file_path = os.path.join(output_path, REPORT_FILE_NAME)
            if os.path.exists(report_file_path):
                logger.info(f"Reading results from file: {report_file_path}")
                try:
                    with open(report_file_path, "r") as report_file:
                        test_results = json.load(report_file)
                    logger.info(f"Loaded test results from file: {json.dumps(test_results, indent=2)}")
                except Exception as e:
                    logger.error(f"Failed to read report file: {e}")
                    test_results = {
                        "passed": 0,
                        "failed": 1,
                        "total": 1,
                        "error": f"Failed to read report file: {e}"
                    }
            else:
                test_results = {
                    "passed": 0,
                    "failed": 1,
                    "total": 1,
                    "error": "No test results returned and no report file found"
                }
        
        logger.info(f"Test execution completed. Results: {test_results}")
        
        # Calculate result value for compatibility
        try:
            if "summary" in test_results:
                # Old format with summary
                result_value = test_results["summary"]["passed"] / test_results["summary"]["total"]
            else:
                # New format
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
            "result_value": 0.0
        }


@activity.defn(name="commit_test_results")
async def commit_test_results_activity(
    result_id: str,
    test_results: Dict[str, Any],
    api_config: Dict[str, Any]
) -> bool:
    """Commit test results to the API."""
    try:
        # Initialize API client
        client = CrudClient(
            url_base=transform_localhost_url(api_config.get("url", "http://localhost:8000")),
            entity_interface=ResultInterface,
            auth=(api_config.get("username", "admin"),api_config.get("password", "admin"))
        )
        
        # Create result update
        result_update = ResultUpdate(
            status=TaskStatus.FINISHED,
            result=test_results["result_value"],
            result_json=test_results
        )
        
        # Update the result directly using the ID
        response = client.update(result_id, result_update)

        return isinstance(response,ResultGet)
        
    except Exception as e:
        raise ApplicationError(message=str(e))


# Workflows
@register_task
@workflow.defn(name="student_testing", sandboxed=False)
class StudentTestingWorkflow(BaseWorkflow):
    """Execute student testing workflow."""
    
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
            parameters: Dict containing test_job and execution_backend_properties
            
        Returns:
            WorkflowResult with test results
        """
        # Extract parameters
        test_job = parameters.get("test_job", {})
        execution_backend_properties = parameters.get("execution_backend_properties", {})
        result_id = parameters.get("result_id")  # Get the database result ID
        
        # Generate a unique job ID for this test run
        job_id = str(uuid.uuid4())
        
        workflow.logger.info(f"Starting student testing for job {job_id}")
        started_at = datetime.utcnow()
        
        with tempfile.TemporaryDirectory() as work_dir:
            try:
                # Parse test job
                job_config = TestJob(**test_job)
                
                # Create temporary directory name (will be created in activity)
                
                #work_dir = f"/tmp/test-{job_id}"
                student_path = os.path.join(work_dir, "student")
                reference_path = os.path.join(work_dir, "reference")
                
                # Clone student repository
                workflow.logger.info("Cloning student repository")
                await workflow.execute_activity(
                    clone_repository_activity,
                    args=[job_config.module.model_dump(), student_path],
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=RetryPolicy(maximum_attempts=3)
                )
                
                # Clone reference repository
                workflow.logger.info("Cloning reference repository")
                await workflow.execute_activity(
                    clone_repository_activity,
                    args=[job_config.reference.model_dump(), reference_path],
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=RetryPolicy(maximum_attempts=3)
                )
                
                # Execute tests
                workflow.logger.info("Executing tests")
                test_results = await workflow.execute_activity(
                    execute_tests_activity,
                    args=[student_path, reference_path, test_job, execution_backend_properties],
                    start_to_close_timeout=timedelta(minutes=20),
                    retry_policy=RetryPolicy(maximum_attempts=1)
                )
                
                # Commit results
                workflow.logger.info("Committing results to API")
                api_config = {
                    "url": os.environ.get("EXECUTION_BACKEND_API_URL", "http://localhost:8000"),
                    "username": os.environ.get("EXECUTION_BACKEND_API_USER", "admin"),
                    "password": os.environ.get("EXECUTION_BACKEND_API_PASSWORD", "admin")
                }
                
                commit_success = await workflow.execute_activity(
                    commit_test_results_activity,
                    args=[result_id, test_results, api_config],
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=RetryPolicy(maximum_attempts=3)
                )

                if commit_success == False:
                    raise Exception({"details": "commit result failed"})
                
                completed_at = datetime.utcnow()
                
                return WorkflowResult(
                    status="completed",
                    result={
                        "test_job_id": job_id,
                        #"test_results": test_results,
                        "api_commit_success": commit_success,
                        "started_at": started_at.isoformat(),
                        "completed_at": completed_at.isoformat(),
                        "duration_seconds": (completed_at - started_at).total_seconds()
                    },
                    metadata={
                        "workflow_type": "student_testing",
                        "passed": test_results["summary"]["passed"],
                        "failed": test_results["summary"]["failed"],
                        "total": test_results["summary"]["total"]
                    }
                )
                
            except Exception as e:
                workflow.logger.error(f"Student testing failed: {str(e)}")
                return WorkflowResult(
                    status="failed",
                    result=None,
                    error=str(e),
                    metadata={
                        "workflow_type": "student_testing",
                        "test_job_id": job_id
                    }
                )

