"""
Temporal worker implementation for running workflows and activities.
"""

import asyncio
import logging
import os
import signal
import sys
from datetime import datetime
from typing import List, Optional
from temporalio.worker import Worker
from temporalio.client import Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

from .temporal_client import (
    get_temporal_client,
    DEFAULT_TASK_QUEUE
)

# Import all workflows and activities
from .temporal_examples import (
    ExampleLongRunningWorkflow,
    ExampleDataProcessingWorkflow,
    ExampleErrorHandlingWorkflow,
    simulate_processing_activity,
    process_data_chunk_activity
)
from .temporal_student_testing import (
    StudentTestingWorkflow,
    fetch_example_version_with_dependencies,
    fetch_submission_artifact,
    execute_tests_activity,
    commit_test_results_activity,
    run_complete_student_test_activity
)
from .temporal_hierarchy_management import (
    CreateOrganizationWorkflow,
    CreateCourseFamilyWorkflow,
    CreateCourseWorkflow,
    DeployComputorHierarchyWorkflow,
    create_organization_activity,
    create_course_family_activity,
    create_course_activity
)
from .temporal_student_template_v2 import (
    GenerateStudentTemplateWorkflowV2,
    generate_student_template_activity_v2
)
from .temporal_assignments_repository import (
    GenerateAssignmentsRepositoryWorkflow,
    generate_assignments_repository_activity
)
from .temporal_documents_sync import (
    SyncDocumentsRepositoryWorkflow,
    sync_documents_repository_activity
)
from .temporal_student_repository import (
    StudentRepositoryCreationWorkflow,
    create_student_repository,
    create_team_repository
)
from .temporal_tutor_testing import (
    TutorTestingWorkflow,
    fetch_tutor_test_input,
    store_tutor_test_artifacts_activity,
    store_tutor_test_result_to_minio,
    run_tutor_test_activity,
)


class TemporalWorker:
    """Temporal worker for executing workflows and activities."""

    def __init__(self, task_queues: Optional[List[str]] = None, heartbeat_interval: int = 300):
        """
        Initialize the worker.

        Args:
            task_queues: List of task queues to listen on. If None, listens on default queue.
            heartbeat_interval: Interval in seconds for heartbeat logging (0 to disable).
        """
        self.task_queues = task_queues or [DEFAULT_TASK_QUEUE]
        self.workers: List[Worker] = []
        self.client: Optional[Client] = None
        self._shutdown = False
        self._heartbeat_interval = heartbeat_interval
        self._start_time: Optional[datetime] = None
        self._tasks_processed = 0

    async def _heartbeat_loop(self):
        """Log periodic heartbeat to show worker is alive."""
        while not self._shutdown:
            await asyncio.sleep(self._heartbeat_interval)
            if not self._shutdown:
                uptime = datetime.utcnow() - self._start_time if self._start_time else "unknown"
                logger.info(
                    f"[HEARTBEAT] Worker alive - queues: {self.task_queues}, "
                    f"uptime: {uptime}, tasks_processed: {self._tasks_processed}"
                )

    async def start(self):
        """Start the worker and begin processing workflows."""
        self._start_time = datetime.utcnow()
        logger.info(f"Starting Temporal worker for queues: {', '.join(self.task_queues)}")
        logger.info(f"Worker start time: {self._start_time.isoformat()}")
        
        # Get client
        self.client = await get_temporal_client()
        
        # Define workflows and activities
        workflows = [
            ExampleLongRunningWorkflow,
            ExampleDataProcessingWorkflow,
            ExampleErrorHandlingWorkflow,
            StudentTestingWorkflow,
            CreateOrganizationWorkflow,
            CreateCourseFamilyWorkflow,
            CreateCourseWorkflow,
            DeployComputorHierarchyWorkflow,
            # DeployExamplesToCourseWorkflow,  # Deprecated - removed
            GenerateStudentTemplateWorkflowV2,
            GenerateAssignmentsRepositoryWorkflow,
            SyncDocumentsRepositoryWorkflow,  # Documents repository sync
            StudentRepositoryCreationWorkflow,  # Student repository forking
            TutorTestingWorkflow,  # Tutor testing (ephemeral, no DB records)
        ]
        
        activities = [
            simulate_processing_activity,
            process_data_chunk_activity,
            fetch_example_version_with_dependencies,  # Fetch and cache reference examples
            fetch_submission_artifact,  # Fetch student submissions
            execute_tests_activity,
            commit_test_results_activity,
            run_complete_student_test_activity,  # Complete test run (all steps on one worker)
            create_organization_activity,
            create_course_family_activity,
            create_course_activity,
            generate_student_template_activity_v2,  # Student template generation
            generate_assignments_repository_activity,  # Assignments init/populate
            sync_documents_repository_activity,  # Documents repository sync from GitLab
            create_student_repository,  # Fork student-template for individual student
            create_team_repository,  # Fork student-template for team
            # Tutor testing activities (no Redis - API handles that)
            fetch_tutor_test_input,
            store_tutor_test_artifacts_activity,
            store_tutor_test_result_to_minio,
            run_tutor_test_activity,
        ]
        
        # Create a worker for each task queue
        for task_queue in self.task_queues:
            logger.info(f"Creating worker for queue: {task_queue}")
            worker = Worker(
                self.client,
                task_queue=task_queue,
                workflows=workflows,
                activities=activities,
            )
            self.workers.append(worker)
            logger.info(f"Worker created for queue: {task_queue}")

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info(f"Worker ready - listening on {len(self.task_queues)} queue(s)")
        logger.info(f"Registered {len(workflows)} workflows and {len(activities)} activities")

        # Start heartbeat loop and workers concurrently
        try:
            tasks = [worker.run() for worker in self.workers]
            if self._heartbeat_interval > 0:
                tasks.append(self._heartbeat_loop())
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Workers cancelled")
        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
        finally:
            await self.shutdown()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down workers...")
        self._shutdown = True
        # Cancel all worker tasks
        for worker in self.workers:
            asyncio.create_task(worker.shutdown())

    async def shutdown(self):
        """Shutdown the worker gracefully."""
        logger.info("Shutting down Temporal workers...")

        # Workers are already shutting down from signal handler
        # Just wait a bit for graceful shutdown
        await asyncio.sleep(1)

        # Close client connection
        if self.client:
            await self.client.close()

        uptime = datetime.utcnow() - self._start_time if self._start_time else "unknown"
        logger.info(f"Workers shut down - uptime: {uptime}, tasks_processed: {self._tasks_processed}")


async def run_worker(queues: Optional[List[str]] = None):
    """
    Run a Temporal worker.
    
    Args:
        queues: Optional list of queue names to process
    """
    worker = TemporalWorker(task_queues=queues)
    await worker.start()


def main():
    """Main entry point for running a worker from command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Temporal worker")
    parser.add_argument(
        "--queues",
        nargs="+",
        help="Task queues to process (default: computor-tasks)",
        default=None
    )
    
    args = parser.parse_args()
    
    # Use specified queues or default
    queues = args.queues
    
    # Run worker
    asyncio.run(run_worker(queues))


if __name__ == "__main__":
    main()
