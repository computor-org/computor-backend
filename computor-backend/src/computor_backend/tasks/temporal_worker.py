"""
Temporal worker implementation for running workflows and activities.
"""

import asyncio
import logging
import signal
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
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

# Workflow/activity registration is derived from the task registry, which is
# populated by importing the modules listed in TEMPORAL_TASK_MODULES (the
# single source of truth). Example workflows are gated by the env flag inside
# import_task_modules(). Adding a new module only requires editing that list.
from .registry import task_registry, import_task_modules
from .worker_settings import get_worker_settings


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
        # Thread pools that run the blocking (sync ``def``) activities off the
        # event loop; one per worker, shut down in ``shutdown()``.
        self._activity_executors: List[ThreadPoolExecutor] = []
        self.client: Optional[Client] = None
        self._shutdown = False
        self._heartbeat_interval = heartbeat_interval
        self._start_time: Optional[datetime] = None
        # Set on shutdown so the heartbeat loop wakes immediately instead of
        # sitting out the rest of its sleep.
        self._shutdown_event: Optional[asyncio.Event] = None

    async def _heartbeat_loop(self):
        """Log periodic heartbeat to show worker is alive.

        Sleeps on the shutdown event rather than a bare ``asyncio.sleep`` — the
        gather in ``start()`` cannot return until this coroutine does, so a plain
        sleep kept a SIGTERM'd worker alive for up to a full interval (300s),
        long past Docker's stop timeout, and the container was SIGKILLed
        mid-test instead of stopping cleanly.
        """
        assert self._shutdown_event is not None
        while not self._shutdown:
            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(), timeout=self._heartbeat_interval
                )
                return  # event set — shutting down
            except asyncio.TimeoutError:
                pass  # normal interval elapsed
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

        # Ensure all task modules are imported (auto-registers workflows and
        # records their activities), then derive registration from the registry.
        import_task_modules()
        workflows = task_registry.list_workflows()
        activities = task_registry.list_activities()

        # Blocking activities are registered as sync ``def`` functions; Temporal
        # requires an activity_executor to run them (and would error at Worker
        # construction otherwise). They run in this thread pool instead of on the
        # asyncio event loop, so a multi-minute clone/build/subprocess no longer
        # stalls heartbeats or starves other activities. Async activities keep
        # running on the loop. max_workers matches max_concurrent_activities
        # (SDK default 100) so the executor is never undersized (the SDK warns
        # otherwise) and activity concurrency is unchanged.
        max_workers = get_worker_settings().activity_executor_max_workers

        # Workers fronting a single non-reentrant resource (the MATLAB worker
        # and its one shared engine) set this to 1; everyone else leaves it
        # unset and keeps the SDK default. The pool is sized down to match,
        # since it never needs more threads than the SDK will hand it work.
        max_concurrent_activities = get_worker_settings().max_concurrent_activities
        if max_concurrent_activities is not None:
            max_workers = max(1, max_concurrent_activities)

        worker_limits = (
            {}
            if max_concurrent_activities is None
            else {"max_concurrent_activities": max_concurrent_activities}
        )

        # Give in-flight activities time to finish when we are asked to stop.
        # Without this the SDK default of 0 cancels a running test the instant
        # the worker is signalled, and test activities are deliberately never
        # retried — so a routine restart destroyed the run.
        graceful_shutdown = timedelta(
            seconds=get_worker_settings().graceful_shutdown_seconds
        )

        # Create a worker for each task queue
        for task_queue in self.task_queues:
            logger.info(f"Creating worker for queue: {task_queue}")
            activity_executor = ThreadPoolExecutor(
                max_workers=max_workers,
                thread_name_prefix=f"activity-{task_queue}",
            )
            self._activity_executors.append(activity_executor)
            worker = Worker(
                self.client,
                task_queue=task_queue,
                workflows=workflows,
                activities=activities,
                activity_executor=activity_executor,
                graceful_shutdown_timeout=graceful_shutdown,
                **worker_limits,
            )
            self.workers.append(worker)
            logger.info(
                f"Worker created for queue: {task_queue} "
                f"(activity thread pool max_workers={max_workers}, "
                f"max_concurrent_activities={max_concurrent_activities or 'SDK default'})"
            )

        # Setup signal handlers. add_signal_handler runs the callback ON the
        # event loop, so scheduling the shutdown coroutines from it is safe;
        # signal.signal() fires on an arbitrary stack where asyncio.create_task
        # can raise "no running event loop".
        self._shutdown_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self._request_shutdown, sig)
            except NotImplementedError:  # pragma: no cover - non-POSIX
                signal.signal(sig, lambda s, _f: self._request_shutdown(s))

        logger.info(f"Worker ready - listening on {len(self.task_queues)} queue(s)")
        logger.info(
            f"Graceful shutdown timeout: {graceful_shutdown.total_seconds():.0f}s "
            f"(container stop_grace_period must be at least this long)"
        )
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

    def _request_shutdown(self, signum):
        """Begin a graceful shutdown (runs on the event loop)."""
        if self._shutdown:
            return
        logger.info(
            f"Received signal {signum}, draining workers "
            f"(in-flight activities get up to "
            f"{get_worker_settings().graceful_shutdown_seconds}s to finish)..."
        )
        self._shutdown = True
        if self._shutdown_event is not None:
            self._shutdown_event.set()
        # Worker.shutdown() stops polling and waits out graceful_shutdown_timeout
        # for running activities before cancelling them.
        for worker in self.workers:
            asyncio.create_task(worker.shutdown())

    async def shutdown(self):
        """Release worker-owned resources after the run loop has ended."""
        logger.info("Shutting down Temporal workers...")

        self._shutdown = True
        if self._shutdown_event is not None:
            self._shutdown_event.set()

        # NOTE: temporalio 1.5.1's Client has no close()/aclose() — calling one
        # raised AttributeError here on every single shutdown, which skipped the
        # thread-pool cleanup below and turned every graceful stop into a
        # traceback. The client owns no resources needing explicit release; the
        # hasattr guard only exists so a future SDK that adds one is honoured.
        close = getattr(self.client, "close", None) if self.client else None
        if callable(close):
            try:
                maybe = close()
                if asyncio.iscoroutine(maybe):
                    await maybe
            except Exception as e:  # pragma: no cover - defensive
                logger.warning(f"Error closing Temporal client: {e}")

        # Release the activity thread pools.
        for executor in self._activity_executors:
            executor.shutdown(wait=False)

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
