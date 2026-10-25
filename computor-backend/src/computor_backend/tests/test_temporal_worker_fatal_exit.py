"""A worker whose polls are refused exits non-zero instead of idling.

temporalio 1.5.1 reports a refused poll (expired token, token without the
queue's namespace) through ``on_fatal_error`` and then can stall inside
``Worker.run()``. These tests drive ``TemporalWorker.start`` with fake SDK
workers that behave that way and check the exit code and the watchdog.
"""

import asyncio
import logging
from types import SimpleNamespace

from temporalio.service import RPCError, RPCStatusCode

from computor_backend.tasks import temporal_worker


def _refused_poll() -> RuntimeError:
    # The shape temporalio 1.5.1 raises (bridge/worker.py -> _activity.py).
    try:
        try:
            raise RuntimeError(
                "Poll failure: Unhandled grpc error when activity polling: Status { "
                'code: PermissionDenied, message: "Request unauthorized." }'
            )
        except RuntimeError as poll:
            raise RuntimeError("Activity worker failed") from poll
    except RuntimeError as failed:
        return failed


def test_authorization_errors_are_recognised_through_the_cause_chain():
    assert temporal_worker.is_authorization_error(_refused_poll())
    assert temporal_worker.is_authorization_error(
        RPCError("Request unauthorized.", RPCStatusCode.UNAUTHENTICATED, b"")
    )
    assert not temporal_worker.is_authorization_error(RuntimeError("Workflow worker failed"))
    assert not temporal_worker.is_authorization_error(
        RPCError("unavailable", RPCStatusCode.UNAVAILABLE, b"")
    )
    assert not temporal_worker.is_authorization_error(None)


def _patch(monkeypatch, behaviour, hard_exits):
    """Fake SDK Worker per queue; ``behaviour[queue]`` decides what run() does."""

    class _Worker:
        def __init__(self, client, *, task_queue, on_fatal_error, **kwargs):
            self.queue = task_queue
            self.on_fatal_error = on_fatal_error
            self.stopped = asyncio.Event()

        async def run(self):
            mode = behaviour.get(self.queue, "idle")
            if mode in ("refused", "refused-stall"):
                await asyncio.sleep(0)
                await self.on_fatal_error(_refused_poll())
                if mode == "refused-stall":
                    await asyncio.Event().wait()  # the SDK never returns
                raise RuntimeError("Activity worker failed")
            await self.stopped.wait()

        async def shutdown(self):
            self.stopped.set()

    async def _client(namespace=None):
        return SimpleNamespace()

    def _hard_exit(code):
        hard_exits.append(code)
        for task in asyncio.all_tasks():
            if task is not asyncio.current_task() and "start" in repr(task.get_coro()):
                task.cancel()

    monkeypatch.setattr(temporal_worker, "Worker", _Worker)
    monkeypatch.setattr(temporal_worker, "get_temporal_client", _client)
    monkeypatch.setattr(temporal_worker, "UNAUTHORIZED_EXIT_GRACE_SECONDS", 0.05)
    monkeypatch.setattr(temporal_worker.TemporalWorker, "_hard_exit", staticmethod(_hard_exit))


def _start(queues):
    worker = temporal_worker.TemporalWorker(task_queues=queues, heartbeat_interval=0)

    async def run():
        return await asyncio.wait_for(worker.start(), timeout=5)

    return asyncio.run(run())


def test_refused_poll_stops_all_queues_and_exits_unauthorized(monkeypatch, caplog):
    hard_exits = []
    _patch(monkeypatch, {"testing": "refused"}, hard_exits)
    with caplog.at_level(logging.CRITICAL, logger=temporal_worker.logger.name):
        code = _start(["testing", "testing-other"])
    assert code == temporal_worker.EXIT_UNAUTHORIZED
    assert hard_exits == []  # the orderly shutdown finished, no watchdog
    assert any("authorization failure" in r.getMessage() for r in caplog.records)


def test_stalled_sdk_shutdown_is_ended_by_the_watchdog(monkeypatch):
    hard_exits = []
    _patch(monkeypatch, {"coder-tasks": "refused-stall"}, hard_exits)
    try:
        _start(["coder-tasks"])
    except asyncio.CancelledError:
        pass
    assert hard_exits == [temporal_worker.EXIT_UNAUTHORIZED]


def test_other_fatal_errors_exit_non_zero(monkeypatch):
    class _Worker:
        def __init__(self, client, **kwargs):
            pass

        async def run(self):
            raise RuntimeError("Workflow worker failed")

        async def shutdown(self):
            return None

    async def _client(namespace=None):
        return SimpleNamespace()

    monkeypatch.setattr(temporal_worker, "Worker", _Worker)
    monkeypatch.setattr(temporal_worker, "get_temporal_client", _client)
    monkeypatch.setattr(
        temporal_worker.TemporalWorker, "_hard_exit", staticmethod(lambda code: None)
    )
    assert _start(["computor-tasks"]) == temporal_worker.EXIT_FATAL


def test_requested_shutdown_exits_zero(monkeypatch):
    hard_exits = []
    _patch(monkeypatch, {}, hard_exits)
    worker = temporal_worker.TemporalWorker(task_queues=["testing"], heartbeat_interval=0)

    async def run():
        task = asyncio.create_task(worker.start())
        while not worker.workers:
            await asyncio.sleep(0.01)
        await asyncio.sleep(0.01)
        worker._request_shutdown(15)
        return await asyncio.wait_for(task, timeout=5)

    assert asyncio.run(run()) == 0
    assert hard_exits == []
