"""
Temporal worker implementation for running workflows and activities.
"""

import asyncio
import logging
import os
import signal
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
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
    namespace_for_queue,
    DEFAULT_TASK_QUEUE
)

# Workflow/activity registration is derived from the task registry, which is
# populated by importing the modules listed in TEMPORAL_TASK_MODULES (the
# single source of truth). Example workflows are gated by the env flag inside
# import_task_modules(). Adding a new module only requires editing that list.
from .registry import task_registry, import_task_modules
from .worker_settings import get_worker_settings

# Exit codes. Docker restarts the container on any non-zero exit
# (restart: unless-stopped), and a restart loop is what the container health
# check and the sentinel see, instead of a process that is up but polls nothing.
EXIT_FATAL = 1
EXIT_UNAUTHORIZED = 3
# After an authorization failure nothing in flight can report its result, so
# there is no reason to wait out the graceful drain before exiting.
UNAUTHORIZED_EXIT_GRACE_SECONDS = 15.0

_AUTH_MARKERS = (
    "PermissionDenied",
    "PERMISSION_DENIED",
    "Unauthenticated",
    "UNAUTHENTICATED",
    "Request unauthorized",
)


def is_authorization_error(error: Optional[BaseException]) -> bool:
    """True when ``error`` or anything in its cause chain is an auth refusal.

    temporalio 1.5.1 reports a refused poll as ``RuntimeError("Activity worker
    failed")`` caused by ``RuntimeError("Poll failure: ... code:
    PermissionDenied ...")`` from the Rust core, so the status only survives in
    the message text; client calls raise ``RPCError`` with a status instead.
    """
    from temporalio.service import RPCError, RPCStatusCode

    seen = 0
    while error is not None and seen < 10:
        if isinstance(error, RPCError) and error.status in (
            RPCStatusCode.PERMISSION_DENIED,
            RPCStatusCode.UNAUTHENTICATED,
        ):
            return True
        text = str(error)
        if any(marker in text for marker in _AUTH_MARKERS):
            return True
        error = error.__cause__ or error.__context__
        seen += 1
    return False


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
        # First fatal worker error; decides the exit code of run_worker().
        self._fatal: Optional[BaseException] = None
        self._exit_watchdog: Optional[asyncio.TimerHandle] = None

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
                uptime = datetime.now(timezone.utc) - self._start_time if self._start_time else "unknown"
                logger.info(
                    f"[HEARTBEAT] Worker alive - queues: {self.task_queues}, "
                    f"uptime: {uptime}"
                )

    async def start(self) -> int:
        """Start the worker, process workflows, and return the exit code.

        0 after a requested shutdown, EXIT_UNAUTHORIZED when Temporal refused
        a poll (e.g. an expired or wrong token), EXIT_FATAL after any other
        fatal worker error.
        """
        # Aware UTC. The worker container runs on UTC by design, but a naive
        # stamp logged its isoformat() with no offset ("2026-08-10T11:03:52"),
        # which reads as local time to anyone correlating it against a wall
        # clock or feeding it to a parser.
        self._start_time = datetime.now(timezone.utc)
        logger.info(f"Starting Temporal worker for queues: {', '.join(self.task_queues)}")
        logger.info(f"Worker start time: {self._start_time.isoformat()}")

        # Get client
        self.client = await get_temporal_client()

        # Ensure all task modules are imported (auto-registers workflows and
        # records their activities), then derive registration from the registry.
        import_task_modules()
        workflows = task_registry.list_workflows()

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
            # Per queue: control-plane-only activities (QUEUE_ACTIVITIES) are
            # absent from the coder and testing workers.
            activities = task_registry.list_activities(task_queue)
            logger.info(f"Creating worker for queue: {task_queue}")
            activity_executor = ThreadPoolExecutor(
                max_workers=max_workers,
                thread_name_prefix=f"activity-{task_queue}",
            )
            self._activity_executors.append(activity_executor)
            # Each queue is polled in its own namespace (TEMPORAL_QUEUE_NAMESPACES).
            namespace = namespace_for_queue(task_queue)
            worker = Worker(
                await get_temporal_client(namespace),
                task_queue=task_queue,
                workflows=workflows,
                activities=activities,
                activity_executor=activity_executor,
                graceful_shutdown_timeout=graceful_shutdown,
                on_fatal_error=self._on_fatal_error,
                **worker_limits,
            )
            self.workers.append(worker)
            logger.info(
                f"Worker created for queue: {task_queue} in namespace {namespace} "
                f"({len(activities)} activities, "
                f"activity thread pool max_workers={max_workers}, "
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

        await self._ensure_support_schedule()

        logger.info(f"Worker ready - listening on {len(self.task_queues)} queue(s)")
        logger.info(
            f"Graceful shutdown timeout: {graceful_shutdown.total_seconds():.0f}s "
            f"(container stop_grace_period must be at least this long)"
        )
        logger.info(f"Registered {len(workflows)} workflows on each queue")

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
            self._begin_fatal_exit(e)
        finally:
            await self.shutdown()
        return self.exit_code()

    def exit_code(self) -> int:
        if self._fatal is None:
            return 0
        return EXIT_UNAUTHORIZED if is_authorization_error(self._fatal) else EXIT_FATAL

    async def _on_fatal_error(self, error: BaseException) -> None:
        """SDK hook: one queue's worker failed and is shutting itself down."""
        self._begin_fatal_exit(error)

    def _begin_fatal_exit(self, error: BaseException) -> None:
        """Stop every queue's worker and make sure the process really exits.

        Without this a worker whose polls were refused stayed up and idle:
        temporalio 1.5.1 logs "Worker failed, shutting down" and then never
        returns from Worker.run() while the core keeps retrying the poll, so
        the container looked healthy and nothing polled the queue. A watchdog
        on the event loop ends the process with the exit code if the orderly
        shutdown does not finish in time.
        """
        if self._fatal is not None:
            return
        self._fatal = error
        code = self.exit_code()
        cause = error
        for _ in range(10):  # the innermost error names the gRPC status
            if cause.__cause__ is None:
                break
            cause = cause.__cause__
        error = str(cause)[:300] or repr(cause)
        if code == EXIT_UNAUTHORIZED:
            grace = UNAUTHORIZED_EXIT_GRACE_SECONDS
            logger.critical(
                "Temporal refused this worker (authorization failure: %s). The "
                "token in TEMPORAL_API_KEY is expired, revoked or lacks write "
                "access to the queue's namespace (TEMPORAL_QUEUE_NAMESPACES). "
                "Exiting with code %d within %.0fs so the container restarts "
                "and the failure is visible.",
                error, code, grace,
            )
        else:
            grace = get_worker_settings().graceful_shutdown_seconds + 15.0
            logger.critical(
                "Temporal worker failed fatally (%s); exiting with code %d "
                "within %.0fs.", error, code, grace,
            )
        self._shutdown = True
        if self._shutdown_event is not None:
            self._shutdown_event.set()
        for worker in self.workers:
            asyncio.ensure_future(worker.shutdown())
        self._exit_watchdog = asyncio.get_running_loop().call_later(
            grace, self._hard_exit, code
        )

    @staticmethod
    def _hard_exit(code: int) -> None:  # pragma: no cover - ends the process
        logger.critical("Worker shutdown did not finish in time; exiting with code %d", code)
        logging.shutdown()
        os._exit(code)

    async def _ensure_support_schedule(self) -> None:
        """The support worker owns the periodic team-mailbox import (#520)."""
        from computor_backend.support.config import SUPPORT_TASK_QUEUE, get_support_settings

        if SUPPORT_TASK_QUEUE not in self.task_queues:
            return
        settings = get_support_settings()
        if not settings.mail_enabled:
            logger.info("Support mail bridge disabled (SUPPORT_MAIL_ENABLED is not true)")
            return
        if not settings.mail_import_enabled:
            logger.info("Support mailbox imports disabled (SUPPORT_MAIL_IMPORT_ENABLED is not true)")
            return
        from .temporal_support_mail import ensure_import_schedule
        try:
            await ensure_import_schedule(self.client, settings.mail_poll_seconds)
        except Exception as e:  # the worker still serves replies without it
            logger.error(f"Could not create the support mail import schedule: {e}", exc_info=True)

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

        uptime = datetime.now(timezone.utc) - self._start_time if self._start_time else "unknown"
        logger.info(f"Workers shut down - uptime: {uptime}")


async def run_worker(queues: Optional[List[str]] = None) -> int:
    """
    Run a Temporal worker.

    Args:
        queues: Optional list of queue names to process
    """
    worker = TemporalWorker(task_queues=queues)
    return await worker.start()


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

    # Run worker; a non-zero code makes Docker restart the container.
    sys.exit(asyncio.run(run_worker(queues)))


if __name__ == "__main__":
    main()
