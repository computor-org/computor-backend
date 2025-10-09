"""
Example Temporal workflow and activity implementations.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict
from temporalio import workflow, activity
from temporalio.common import RetryPolicy

from .temporal_base import BaseWorkflow, BaseActivity, WorkflowResult, WorkflowProgress
from .registry import register_task


# Activities
@activity.defn(name="simulate_processing")
async def simulate_processing_activity(duration: int, message: str) -> Dict[str, Any]:
    """Simulate processing work."""
    start_time = datetime.utcnow()
    
    # Simulate work
    await asyncio.sleep(duration)
    
    end_time = datetime.utcnow()
    
    return {
        "message": message,
        "duration_requested": duration,
        "duration_actual": (end_time - start_time).total_seconds(),
        "started_at": start_time.isoformat(),
        "completed_at": end_time.isoformat(),
    }


@activity.defn(name="process_data_chunk")
async def process_data_chunk_activity(chunk_data: list, operation: str) -> Dict[str, Any]:
    """Process a chunk of data."""
    # Simulate data processing
    await asyncio.sleep(0.5)  # Simulate processing time
    
    if operation == "sum":
        result = sum(chunk_data)
    elif operation == "count":
        result = len(chunk_data)
    elif operation == "max":
        result = max(chunk_data) if chunk_data else None
    else:
        result = chunk_data
    
    return {
        "chunk_size": len(chunk_data),
        "operation": operation,
        "result": result
    }


# Workflows
@register_task
@workflow.defn(name="example_long_running", sandboxed=False)
class ExampleLongRunningWorkflow(BaseWorkflow):
    """Example workflow that simulates a long-running operation."""
    
    @classmethod
    def get_name(cls) -> str:
        return "example_long_running"
    
    @classmethod
    def get_task_queue(cls) -> str:
        return "computor-tasks"
    
    @classmethod
    def get_execution_timeout(cls) -> timedelta:
        return timedelta(minutes=5)
    
    @workflow.run
    async def run(self, parameters: dict) -> WorkflowResult:
        """
        Run the long-running workflow.
        
        Args:
            parameters: Dictionary containing duration and message
            
        Returns:
            WorkflowResult with execution details
        """
        # Extract parameters with defaults
        duration = parameters.get('duration', 60)
        message = parameters.get('message', 'Processing...')
        
        # Ensure duration is an integer
        if isinstance(duration, str):
            duration = int(duration)
        
        # Record progress
        workflow.logger.info(f"Starting long-running task for {duration} seconds")
        
        # Execute activity with retry policy
        result = await workflow.execute_activity(
            simulate_processing_activity,
            args=[duration, message],
            start_to_close_timeout=timedelta(seconds=duration + 30),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=1),
                backoff_coefficient=2.0,
                maximum_interval=timedelta(seconds=10),
                maximum_attempts=3,
            )
        )
        
        workflow.logger.info("Long-running task completed")
        
        return WorkflowResult(
            status="completed",
            result=result,
            metadata={"workflow_type": "long_running"}
        )


@register_task
@workflow.defn(name="example_data_processing", sandboxed=False)
class ExampleDataProcessingWorkflow(BaseWorkflow):
    """Example workflow for processing data in chunks."""
    
    @classmethod
    def get_name(cls) -> str:
        return "example_data_processing"
    
    @classmethod
    def get_execution_timeout(cls) -> timedelta:
        return timedelta(minutes=10)
    
    @workflow.run
    async def run(self, parameters: dict) -> WorkflowResult:
        """
        Process data in chunks.
        
        Args:
            parameters: Dictionary containing data, chunk_size, and operation
            
        Returns:
            WorkflowResult with processing results
        """
        # Extract parameters with defaults
        data_size = parameters.get('data_size', 100)
        chunk_size = parameters.get('chunk_size', 10)
        operation = parameters.get('operation', 'sum')
        
        # Generate sample data if data_size is provided instead of actual data
        if isinstance(data_size, int):
            data = list(range(1, data_size + 1))
        else:
            data = parameters.get('data', list(range(1, 101)))
        
        workflow.logger.info(f"Processing {len(data)} items in chunks of {chunk_size} using {operation} operation")
        
        # Split data into chunks
        chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
        chunk_results = []
        
        # Process each chunk as an activity
        for i, chunk in enumerate(chunks):
            workflow.logger.info(f"Processing chunk {i + 1}/{len(chunks)}")
            
            result = await workflow.execute_activity(
                process_data_chunk_activity,
                args=[chunk, operation],
                start_to_close_timeout=timedelta(minutes=1),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    backoff_coefficient=2.0,
                    maximum_attempts=3,
                )
            )
            chunk_results.append(result)
        
        # Aggregate results
        total_processed = sum(r["chunk_size"] for r in chunk_results)
        
        # Calculate final result based on operation
        if operation == "sum":
            final_result = sum(r["result"] for r in chunk_results if r["result"] is not None)
        elif operation == "count":
            final_result = total_processed
        elif operation == "max":
            values = [r["result"] for r in chunk_results if r["result"] is not None]
            final_result = max(values) if values else None
        else:
            final_result = chunk_results
        
        workflow.logger.info(f"Data processing completed. Processed {total_processed} items")
        
        return WorkflowResult(
            status="completed",
            result={
                "total_items": len(data),
                "chunks_processed": len(chunks),
                "chunk_size": chunk_size,
                "operation": operation,
                "final_result": final_result,
                "chunk_results": chunk_results
            },
            metadata={"workflow_type": "data_processing"}
        )


@register_task  
@workflow.defn(name="example_error_handling", sandboxed=False)
class ExampleErrorHandlingWorkflow(BaseWorkflow):
    """Example workflow demonstrating error handling."""
    
    @classmethod
    def get_name(cls) -> str:
        return "example_error_handling"
    
    @workflow.run
    async def run(self, parameters: dict) -> WorkflowResult:
        """
        Demonstrate error handling in workflows.
        
        Args:
            parameters: Dictionary containing should_fail, retry_count, and fail_at_step
            
        Returns:
            WorkflowResult
        """
        # Extract parameters with defaults
        should_fail = parameters.get('should_fail', False)
        retry_count = parameters.get('retry_count', 0)
        fail_at_step = parameters.get('fail_at_step', 1)
        
        # Ensure boolean conversion
        if isinstance(should_fail, str):
            should_fail = should_fail.lower() in ('true', '1', 'yes')
            
        attempts = 0
        
        while attempts <= retry_count:
            try:
                # Use fail_at_step to determine when to fail
                if should_fail and attempts < fail_at_step:
                    workflow.logger.warning(f"Simulating failure at step {attempts + 1} (configured to fail at step {fail_at_step})")
                    raise Exception(f"Simulated failure at step {attempts + 1}")
                
                # Success case
                workflow.logger.info(f"Processing succeeded on attempt {attempts + 1}")
                return WorkflowResult(
                    status="completed",
                    result={
                        "message": "Task completed successfully",
                        "attempts": attempts + 1,
                        "retry_count": retry_count
                    }
                )
                
            except Exception as e:
                attempts += 1
                if attempts > retry_count:
                    workflow.logger.error(f"All retries exhausted: {str(e)}")
                    return WorkflowResult(
                        status="failed",
                        result=None,
                        error=str(e),
                        metadata={"attempts": attempts}
                    )
                
                # Wait before retry (max 60 seconds)
                sleep_seconds = min(2 ** attempts, 60)
                await asyncio.sleep(sleep_seconds)
        
        # Should not reach here
        return WorkflowResult(
            status="failed",
            result=None,
            error="Unexpected workflow state"
        )