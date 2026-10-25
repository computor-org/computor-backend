"""Is anyone actually listening on this Temporal task queue?

``Service.config.temporal.task_queue`` is free-form operator data. Nothing
cross-checks it against the queues the deployed workers were started with
(``--queues=...`` in compose), so a typo, or a queue whose worker was never
deployed, was accepted silently: the workflow started, sat unclaimed, and the
student watched a QUEUED test until the execution timeout expired. The failure
looked like a broken test rather than a misconfigured service.

Temporal already knows the answer — a queue with no pollers has no worker — so
ask it and refuse the submission up front with a message naming the queue.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def queue_poller_count(task_queue: str) -> Optional[int]:
    """Return the number of workers polling ``task_queue``.

    ``None`` means "could not determine" (Temporal unreachable, API shape
    changed) — callers must treat that as "assume healthy" rather than block a
    test run on the health check itself failing.
    """
    try:
        import temporalio.api.taskqueue.v1 as taskqueue
        import temporalio.api.workflowservice.v1 as workflowservice
        from temporalio.api.enums.v1 import TaskQueueType

        from computor_backend.tasks.temporal_client import (
            get_temporal_client,
            namespace_for_queue,
        )

        client = await get_temporal_client(namespace_for_queue(task_queue))
        response = await client.workflow_service.describe_task_queue(
            workflowservice.DescribeTaskQueueRequest(
                namespace=client.namespace,
                task_queue=taskqueue.TaskQueue(name=task_queue),
                # Workflow pollers: a worker registers the workflow type on the
                # queue it was started with, so their absence is exactly the
                # "no worker deployed for this queue" condition.
                task_queue_type=TaskQueueType.TASK_QUEUE_TYPE_WORKFLOW,
            )
        )
        return len(response.pollers)
    except Exception as e:
        logger.warning("Could not describe task queue %r: %s", task_queue, e)
        return None


async def assert_queue_has_worker(task_queue: str, service_name: str = "") -> None:
    """Raise BadRequestException when no worker polls ``task_queue``.

    Fails open: if Temporal cannot be asked, the submission proceeds (the
    workflow start immediately after would surface a real outage anyway).
    """
    from computor_backend.exceptions import BadRequestException

    pollers = await queue_poller_count(task_queue)
    if pollers is None or pollers > 0:
        return

    who = f" for service '{service_name}'" if service_name else ""
    raise BadRequestException(
        error_code="EXT_005",
        detail=(
            f"No testing worker is listening on task queue '{task_queue}'{who}. "
            f"The queue name in the service configuration "
            f"(config.temporal.task_queue) must match a deployed worker's "
            f"--queues value; otherwise the test would wait indefinitely. "
            f"Check that the worker container for this queue is running."
        ),
        context={"task_queue": task_queue, "service": service_name},
    )


async def poller_report(task_queues: list[str]) -> dict:
    """``{queue: {"namespace": ns, "pollers": n or None}}`` for monitoring."""
    from computor_backend.tasks.temporal_client import namespace_for_queue

    report = {}
    for queue in task_queues:
        report[queue] = {
            "namespace": namespace_for_queue(queue),
            "pollers": await queue_poller_count(queue),
        }
    return report


def main(argv: Optional[list[str]] = None) -> int:
    """Print the poller report as one JSON line (used by the host sentinel).

    ``python -m computor_backend.tasks.queue_health computor-tasks testing``
    runs inside the API container, which holds the control-plane token and
    TEMPORAL_QUEUE_NAMESPACES, so each queue is asked in its own namespace.
    """
    import argparse
    import asyncio
    import json

    parser = argparse.ArgumentParser(description="Report Temporal pollers per task queue")
    parser.add_argument("queues", nargs="+")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.ERROR)
    print(json.dumps(asyncio.run(poller_report(args.queues)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
