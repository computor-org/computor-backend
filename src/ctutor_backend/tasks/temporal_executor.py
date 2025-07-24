"""
Task executor implementation using Temporal.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List
from temporalio.client import WorkflowHandle, WorkflowExecutionStatus
from temporalio.common import WorkflowIDReusePolicy
from .temporal_client import get_temporal_client, get_task_queue_by_priority
from .temporal_base import WorkflowResult
from .base import TaskStatus, TaskResult, TaskInfo, TaskSubmission
from .registry import task_registry


class TemporalTaskExecutor:
    """
    Task executor using Temporal for managing long-running operations.
    """
    
    def __init__(self):
        """Initialize task executor."""
        # Status mapping from Temporal to our TaskStatus
        self._status_mapping = {
            WorkflowExecutionStatus.RUNNING: TaskStatus.STARTED,
            WorkflowExecutionStatus.COMPLETED: TaskStatus.FINISHED,
            WorkflowExecutionStatus.FAILED: TaskStatus.FAILED,
            WorkflowExecutionStatus.CANCELED: TaskStatus.CANCELLED,
            WorkflowExecutionStatus.TERMINATED: TaskStatus.CANCELLED,
            WorkflowExecutionStatus.CONTINUED_AS_NEW: TaskStatus.STARTED,
            WorkflowExecutionStatus.TIMED_OUT: TaskStatus.FAILED,
        }
    
    async def submit_task(self, submission: TaskSubmission) -> str:
        """
        Submit a task for execution.
        
        Args:
            submission: Task submission details
            
        Returns:
            Workflow ID for tracking
            
        Raises:
            KeyError: If task type is not registered
            Exception: If task submission fails
        """
        # Validate task exists
        workflow_class = task_registry.get_task(submission.task_name)
        
        # Get Temporal client
        client = await get_temporal_client()
        
        # Generate unique workflow ID
        workflow_id = f"{submission.task_name}-{uuid.uuid4()}"
        
        # Get queue name based on priority
        task_queue = get_task_queue_by_priority(submission.priority)
        
        # Start workflow
        handle = await client.start_workflow(
            workflow=submission.task_name,
            arg=submission.parameters,
            id=workflow_id,
            task_queue=task_queue,
            execution_timeout=workflow_class.get_execution_timeout(),
            retry_policy=workflow_class.get_retry_policy(),
            id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE,
        )
        
        return workflow_id
    
    async def get_task_status(self, task_id: str) -> TaskInfo:
        """
        Get task execution status and information.
        
        Args:
            task_id: Task/Workflow ID
            
        Returns:
            Task information and status
            
        Raises:
            Exception: If task not found or status query fails
        """
        client = await get_temporal_client()
        
        try:
            # Get workflow handle
            handle = client.get_workflow_handle(task_id)
            
            # Describe workflow to get status
            description = await handle.describe()
            
            # Map Temporal status to our TaskStatus
            status = self._status_mapping.get(
                description.status,
                TaskStatus.QUEUED
            )
            
            # Extract task name from workflow ID
            task_name = task_id.split('-')[0] if '-' in task_id else "unknown"
            
            # Build task info
            task_info = TaskInfo(
                task_id=task_id,
                task_name=task_name,
                status=status,
                created_at=description.start_time or datetime.now(timezone.utc),
                started_at=description.start_time,
                finished_at=description.close_time,
                error="Task failed" if status == TaskStatus.FAILED else None,
                worker=description.task_queue,
                queue=description.task_queue,
            )
            
            return task_info
            
        except Exception as e:
            # Handle workflow not found
            raise Exception(f"Task {task_id} not found: {str(e)}")
    
    async def get_task_result(self, task_id: str) -> TaskResult:
        """
        Get task execution result.
        
        Args:
            task_id: Task/Workflow ID
            
        Returns:
            Task execution result
            
        Raises:
            Exception: If task not found or result unavailable
        """
        client = await get_temporal_client()
        
        try:
            # Get workflow handle
            handle = client.get_workflow_handle(task_id)
            
            # Get workflow result
            try:
                result = await handle.result()
                
                # Convert WorkflowResult to TaskResult
                return TaskResult(
                    task_id=task_id,
                    status=TaskStatus.FINISHED,
                    result=result.result if isinstance(result, WorkflowResult) else result,
                    error=None,
                    created_at=datetime.now(timezone.utc),
                    finished_at=datetime.now(timezone.utc),
                )
            except Exception as e:
                # Workflow failed
                description = await handle.describe()
                return TaskResult(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    result=None,
                    error=str(e),
                    created_at=description.start_time or datetime.now(timezone.utc),
                    started_at=description.start_time,
                    finished_at=description.close_time,
                )
                
        except Exception as e:
            raise Exception(f"Failed to get result for task {task_id}: {str(e)}")
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task.
        
        Args:
            task_id: Task/Workflow ID
            
        Returns:
            True if cancelled successfully
            
        Raises:
            Exception: If task not found or cancellation fails
        """
        client = await get_temporal_client()
        
        try:
            # Get workflow handle
            handle = client.get_workflow_handle(task_id)
            
            # Cancel the workflow
            await handle.cancel()
            
            return True
            
        except Exception as e:
            raise Exception(f"Failed to cancel task {task_id}: {str(e)}")
    
    async def list_workers(self) -> List[Dict[str, Any]]:
        """
        List active workers.
        
        Note: Temporal doesn't provide direct worker listing through the client.
        This would need to be implemented through the Temporal web UI or CLI.
        
        Returns:
            List of worker information
        """
        # Temporal doesn't expose worker information directly through the client
        # This would need to be queried through the Temporal server's system workflows
        # or monitoring endpoints
        return []
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics.
        
        Note: Temporal doesn't provide direct queue stats through the client.
        This would need to be implemented through the Temporal web UI or metrics.
        
        Returns:
            Queue statistics
        """
        # Temporal doesn't expose queue statistics directly through the client
        # This would need to be queried through Temporal's metrics endpoints
        return {
            "queues": {
                "computor-tasks": {"pending": 0, "active": 0},
                "computor-high-priority": {"pending": 0, "active": 0},
                "computor-low-priority": {"pending": 0, "active": 0},
            }
        }
    
    async def list_tasks(self, limit: int = 100, offset: int = 0, status: Optional[str] = None) -> Dict[str, Any]:
        """
        List tasks with pagination and filtering.
        
        Args:
            limit: Maximum number of tasks to return
            offset: Number of tasks to skip
            status: Optional status filter
            
        Returns:
            Dictionary with task list and pagination info
        """
        client = await get_temporal_client()
        
        try:
            # Use Temporal's list_workflows API to get workflows
            from temporalio.client import WorkflowExecutionStatus
            
            # Build query filter
            query_parts = []
            
            # Note: Status filtering requires proper Temporal query syntax
            # For now, we'll filter in Python after fetching results
            status_filter = None
            if status:
                status_mapping = {
                    "PENDING": [WorkflowExecutionStatus.RUNNING],
                    "STARTED": [WorkflowExecutionStatus.RUNNING], 
                    "FINISHED": [WorkflowExecutionStatus.COMPLETED],
                    "SUCCESS": [WorkflowExecutionStatus.COMPLETED],
                    "FAILED": [WorkflowExecutionStatus.FAILED, WorkflowExecutionStatus.TIMED_OUT],
                    "CANCELLED": [WorkflowExecutionStatus.CANCELED, WorkflowExecutionStatus.TERMINATED],
                    "REVOKED": [WorkflowExecutionStatus.TERMINATED]
                }
                status_filter = status_mapping.get(status.upper(), [])
            
            # Build query string
            query = " AND ".join(query_parts) if query_parts else ""
            
            # List workflows using Temporal's visibility API
            workflows = []
            async for workflow in client.list_workflows(
                query=query or None,
                page_size=min(limit * 2, 1000)  # Fetch more to account for filtering
            ):
                # Apply status filter if specified
                if status_filter and workflow.status not in status_filter:
                    continue
                
                # Convert to our TaskInfo format
                task_info = {
                    "task_id": workflow.id,
                    "task_name": workflow.workflow_type,
                    "status": self._status_mapping.get(workflow.status, TaskStatus.QUEUED).value,
                    "created_at": workflow.start_time,
                    "started_at": workflow.start_time,
                    "finished_at": workflow.close_time,
                    "error": None,
                    "worker": workflow.task_queue or "unknown",
                    "queue": workflow.task_queue or "unknown",
                    "workflow_id": workflow.id,
                    "run_id": workflow.run_id,
                    "execution_time": workflow.execution_time,
                    "history_length": workflow.history_length
                }
                workflows.append(task_info)
                
                # Apply manual offset/limit since Temporal doesn't support offset directly
                if len(workflows) >= limit + offset:
                    break
            
            # Apply offset and limit
            start_idx = min(offset, len(workflows))
            end_idx = min(offset + limit, len(workflows))
            paginated_workflows = workflows[start_idx:end_idx]
            
            return {
                "tasks": paginated_workflows,
                "total": len(workflows),  # This is approximate since we don't get total count from Temporal
                "limit": limit,
                "offset": offset,
                "has_more": len(workflows) >= limit + offset
            }
            
        except Exception as e:
            # Fallback to empty result on error, but log it
            print(f"Error listing workflows: {e}")
            return {
                "tasks": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
                "has_more": False,
                "error": str(e)
            }
    
    async def delete_task(self, task_id: str) -> bool:
        """
        Delete a task from history.
        
        Note: Temporal doesn't support deleting workflow history directly.
        This would need to be implemented through retention policies.
        
        Args:
            task_id: Task/Workflow ID
            
        Returns:
            True if deleted successfully
        """
        # Temporal doesn't support direct deletion of workflow history
        # This would need to be configured through retention policies
        return False
    
    async def get_worker_status(self) -> Dict[str, Any]:
        """
        Get worker status information.
        
        Returns:
            Worker status information
        """
        # Temporal doesn't expose worker status directly through the client
        # This would need to be queried through Temporal's system workflows
        return {
            "workers": [],
            "backend": "temporal",
            "status": "healthy",
            "broker_status": "connected"
        }


# Singleton instance
_executor: Optional[TemporalTaskExecutor] = None


def get_task_executor() -> TemporalTaskExecutor:
    """
    Get the task executor instance.
    
    Returns:
        Task executor instance
    """
    global _executor
    if _executor is None:
        _executor = TemporalTaskExecutor()
    return _executor