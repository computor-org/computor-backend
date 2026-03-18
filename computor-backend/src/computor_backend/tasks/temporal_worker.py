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

# Import all temporal modules — each exports WORKFLOWS and ACTIVITIES lists.
# Adding a new workflow/activity only requires updating the defining module.
from . import (
    temporal_examples,
    temporal_student_testing,
    temporal_hierarchy_management,
    temporal_student_template_v2,
    temporal_assignments_repository,
    temporal_documents_sync,
    temporal_student_repository,
    temporal_tutor_testing,
    temporal_coder_setup,
)

_TEMPORAL_MODULES = [
    temporal_examples,
    temporal_student_testing,
    temporal_hierarchy_management,
    temporal_student_template_v2,
    temporal_assignments_repository,
    temporal_documents_sync,
    temporal_student_repository,
    temporal_tutor_testing,
    temporal_coder_setup,
]


def _collect_from_modules(attr: str) -> list:
    """Collect WORKFLOWS or ACTIVITIES from all temporal modules."""
    items = []
    for mod in _TEMPORAL_MODULES:
        items.extend(getattr(mod, attr, []))
    return items


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

    async def _heartbeat_loop(self):
        """Log periodic heartbeat to show worker is alive."""
        while not self._shutdown:
            await asyncio.sleep(self._heartbeat_interval)
            if not self._shutdown:
                uptime = datetime.utcnow() - self._start_time if self._start_time else "unknown"
                logger.info(
                    f"[HEARTBEAT] Worker alive - queues: {self.task_queues}, "
                    f"uptime: {uptime}"
                )

    async def start(self):
        """Start the worker and begin processing workflows."""
        self._start_time = datetime.utcnow()
        logger.info(f"Starting Temporal worker for queues: {', '.join(self.task_queues)}")
        logger.info(f"Worker start time: {self._start_time.isoformat()}")

        # Get client
        self.client = await get_temporal_client()

        # Collect workflows and activities from all temporal modules
        workflows = _collect_from_modules("WORKFLOWS")
        activities = _collect_from_modules("ACTIVITIES")

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
        logger.info(f"Workers shut down - uptime: {uptime}")


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
