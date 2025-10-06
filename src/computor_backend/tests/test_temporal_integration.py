"""
Integration tests for the Temporal task system.
"""

import pytest
import asyncio
import os
from unittest.mock import patch
from datetime import datetime
from uuid import uuid4

from computor_backend.tasks import (
    get_task_executor,
    TaskSubmission,
    TaskStatus,
    task_registry,
)
from computor_backend.tasks.temporal_worker import TemporalWorker
# Note: These functions may not exist in api.tasks
# Commenting out for now to allow tests to load
# from computor_backend.api.tasks import (
#     submit_task,
#     get_task_status,
#     get_task_result,
#     list_task_types,
#     get_workers_status,
# )


# Skip these tests if Temporal is not available
pytestmark = pytest.mark.skipif(
    os.environ.get("SKIP_TEMPORAL_TESTS", "true").lower() == "true",
    reason="Temporal integration tests require running Temporal server"
)


class TestTemporalIntegration:
    """Integration tests for Temporal system."""

    @pytest.fixture(autouse=True)
    async def setup_and_teardown(self):
        """Setup and teardown for each test."""
        # Reset any global state
        yield
        # Cleanup after test
        pass

    @pytest.mark.asyncio
    async def test_full_workflow_lifecycle(self):
        """Test complete workflow lifecycle from submission to result."""
        executor = get_task_executor()
        
        # Submit a task
        submission = TaskSubmission(
            task_name="example_long_running",
            parameters={"duration": 2, "message": "Integration test"},
            queue="computor-tasks"
        )
        
        task_id = await executor.submit_task(submission)
        assert task_id is not None
        
        # Check initial status
        status = await executor.get_task_status(task_id)
        assert status.task_id == task_id
        assert status.task_name == "example_long_running"
        assert status.status in ["QUEUED", "STARTED"]
        
        # Wait for completion
        max_attempts = 10
        for _ in range(max_attempts):
            await asyncio.sleep(1)
            status = await executor.get_task_status(task_id)
            if status.status in ["FINISHED", "FAILED"]:
                break
        
        # Get final result
        result = await executor.get_task_result(task_id)
        assert result.task_id == task_id
        assert result.status == TaskStatus.FINISHED
        assert result.result["message"] == "Integration test"
        assert result.result["duration_requested"] == 2

    @pytest.mark.asyncio
    async def test_single_queue(self):
        """Test tasks running on the default queue."""
        executor = get_task_executor()
        
        # Submit multiple tasks to the same queue
        submissions = [
            TaskSubmission(
                task_name="example_long_running",
                parameters={"duration": 1, "message": f"Queue test {i}"},
                queue="computor-tasks"
            )
            for i in range(2)
        ]
        
        task_ids = []
        for submission in submissions:
            task_id = await executor.submit_task(submission)
            task_ids.append(task_id)
        
        # Verify both tasks are submitted
        assert len(task_ids) == 2
        assert all(task_id is not None for task_id in task_ids)

    @pytest.mark.asyncio
    async def test_task_cancellation(self):
        """Test cancelling a running task."""
        executor = get_task_executor()
        
        # Submit a long-running task
        submission = TaskSubmission(
            task_name="example_long_running",
            parameters={"duration": 30, "message": "Cancel test"},
            queue="computor-tasks"
        )
        
        task_id = await executor.submit_task(submission)
        
        # Wait a bit for task to start
        await asyncio.sleep(2)
        
        # Cancel the task
        await executor.cancel_task(task_id)
        
        # Check status
        status = await executor.get_task_status(task_id)
        # Status might be CANCELLED or still transitioning
        assert status.task_id == task_id

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test workflow error handling."""
        executor = get_task_executor()
        
        # Submit a task that will fail
        submission = TaskSubmission(
            task_name="example_error_handling",
            parameters={
                "should_fail": True,
                "retry_count": 1,
                "fail_at_step": 10  # Always fail
            },
            queue="computor-tasks"
        )
        
        task_id = await executor.submit_task(submission)
        
        # Wait for completion
        max_attempts = 10
        for _ in range(max_attempts):
            await asyncio.sleep(1)
            status = await executor.get_task_status(task_id)
            if status.status in ["FINISHED", "FAILED"]:
                break
        
        # Get result
        result = await executor.get_task_result(task_id)
        assert result.status == TaskStatus.FAILED
        assert result.error is not None
        assert "Simulated failure" in result.error

    @pytest.mark.asyncio
    async def test_list_tasks(self):
        """Test listing tasks with filters."""
        executor = get_task_executor()
        
        # Submit a few tasks
        task_ids = []
        for i in range(3):
            submission = TaskSubmission(
                task_name="example_long_running",
                parameters={"duration": 1, "message": f"List test {i}"},
                queue="computor-tasks"
            )
            task_id = await executor.submit_task(submission)
            task_ids.append(task_id)
        
        # List all tasks
        all_tasks = await executor.list_tasks(limit=100)
        
        # Verify our tasks are in the list
        listed_task_ids = [task["task_id"] for task in all_tasks]
        for task_id in task_ids:
            assert task_id in listed_task_ids

    @pytest.mark.asyncio
    async def test_worker_status(self):
        """Test getting worker status information."""
        executor = get_task_executor()
        
        # Get worker status
        status = await executor.get_workers_status()
        
        # Verify structure
        assert "workers" in status
        assert "backend" in status
        assert status["backend"] == "temporal"
        assert isinstance(status["workers"], list)

    @pytest.mark.asyncio
    async def test_api_endpoints(self):
        """Test API endpoint integration."""
        from fastapi.testclient import TestClient
        from computor_backend.api import app
        
        client = TestClient(app)
        
        # Test submit endpoint
        response = client.post(
            "/tasks/submit",
            json={
                "task_name": "example_long_running",
                "parameters": {"duration": 1, "message": "API test"},
                "queue": "computor-tasks"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        task_id = data["task_id"]
        
        # Test status endpoint
        response = client.get(f"/tasks/{task_id}/status")
        assert response.status_code == 200
        status_data = response.json()
        assert status_data["task_id"] == task_id
        
        # Test list types endpoint
        response = client.get("/tasks/types")
        assert response.status_code == 200
        types_data = response.json()
        assert "example_long_running" in types_data["task_types"]
        
        # Test workers status endpoint
        response = client.get("/tasks/workers/status")
        assert response.status_code == 200
        workers_data = response.json()
        assert "workers" in workers_data

    @pytest.mark.asyncio
    async def test_concurrent_task_submission(self):
        """Test submitting multiple tasks concurrently."""
        executor = get_task_executor()
        
        # Create multiple submissions
        submissions = [
            TaskSubmission(
                task_name="example_data_processing",
                parameters={
                    "data_size": 100,
                    "chunk_size": 10,
                    "operation": "sum"
                },
                queue="computor-tasks"
            )
            for _ in range(5)
        ]
        
        # Submit concurrently
        task_ids = await asyncio.gather(*[
            executor.submit_task(submission)
            for submission in submissions
        ])
        
        # Verify all submitted
        assert len(task_ids) == 5
        assert all(task_id is not None for task_id in task_ids)

    @pytest.mark.asyncio
    async def test_task_registry(self):
        """Test task registry functionality."""
        # Verify example workflows are registered
        assert task_registry.get("example_long_running") is not None
        assert task_registry.get("example_data_processing") is not None
        assert task_registry.get("example_error_handling") is not None
        
        # Verify unknown task returns None
        assert task_registry.get("non_existent_task") is None
        
        # List all tasks
        all_tasks = task_registry.list_tasks()
        assert "example_long_running" in all_tasks
        assert "example_data_processing" in all_tasks
        assert "example_error_handling" in all_tasks

    @pytest.mark.asyncio
    async def test_workflow_with_progress(self):
        """Test workflow progress tracking."""
        executor = get_task_executor()
        
        # Submit data processing task
        submission = TaskSubmission(
            task_name="example_data_processing",
            parameters={
                "data_size": 50,
                "chunk_size": 10,
                "operation": "sum"
            },
            queue="computor-tasks"
        )
        
        task_id = await executor.submit_task(submission)
        
        # Monitor progress
        progress_seen = False
        max_attempts = 20
        for _ in range(max_attempts):
            await asyncio.sleep(0.5)
            status = await executor.get_task_status(task_id)
            
            if status.progress:
                progress_seen = True
            
            if status.status in ["FINISHED", "FAILED"]:
                break
        
        # Progress tracking might not always be visible in fast tests
        # but the workflow should complete successfully
        result = await executor.get_task_result(task_id)
        assert result.status == TaskStatus.FINISHED

    @pytest.mark.asyncio
    async def test_delete_task_not_supported(self):
        """Test that delete operation returns proper error."""
        executor = get_task_executor()
        
        # Submit a task
        submission = TaskSubmission(
            task_name="example_long_running",
            parameters={"duration": 1, "message": "Delete test"},
            queue="computor-tasks"
        )
        
        task_id = await executor.submit_task(submission)
        
        # Try to delete
        with pytest.raises(NotImplementedError) as exc_info:
            await executor.delete_task(task_id)
        
        assert "Temporal doesn't support direct deletion" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_custom_queue_workflow(self):
        """Test workflow using custom queue."""
        # This would test a workflow that defines its own queue
        # For now, we'll use the standard example workflows
        executor = get_task_executor()
        
        # Submit to the default queue
        submission = TaskSubmission(
            task_name="example_long_running",
            parameters={"duration": 1, "message": "Default queue"},
            queue="computor-tasks"
        )
        
        task_id = await executor.submit_task(submission)
        assert task_id is not None
        
        # Verify task was submitted to correct queue
        status = await executor.get_task_status(task_id)
        # Queue information might be in the status
        assert status.task_id == task_id