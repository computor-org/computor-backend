"""Execution workflows in their own Temporal namespaces (TEMPORAL_QUEUE_NAMESPACES).

Unit tests cover the queue -> namespace mapping and the executor's routing.
The integration tests run a local Temporal dev server with three namespaces
(``WorkflowEnvironment.start_local``, as in test_rollout_history_secrets): the
control-plane worker polls the main namespace, the Coder and testing workers
poll their own, and the API-side executor starts, finds and lists workflows
across them. Coder and the database are faked as in the rollout history test.
"""

import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from temporalio import workflow
from temporalio.service import RPCError, RPCStatusCode
from temporalio.testing import ActivityEnvironment, WorkflowEnvironment
from temporalio.worker import Worker

from computor_backend.tasks import temporal_client
from computor_backend.tasks import temporal_coder_setup as setup
from computor_backend.tasks.registry import import_task_modules, task_registry
from computor_backend.tasks.temporal_client import (
    configured_namespaces,
    get_temporal_client,
    namespace_for_queue,
    parse_queue_namespaces,
)
from computor_backend.tasks.temporal_executor import TaskNotFoundError, TemporalTaskExecutor
from computor_backend.tasks.worker_settings import get_worker_settings
from computor_backend.tests.test_rollout_history_secrets import fake_coder  # noqa: F401
from computor_types.tasks import TaskStatus, TaskSubmission

MAIN = "default"
CODER_NS = "computor-coder"
GRADING_NS = "computor-grading"
MAPPING = f"coder-tasks={CODER_NS},testing*={GRADING_NS}"


@pytest.fixture
def split_namespaces(monkeypatch):
    monkeypatch.setenv("TEMPORAL_NAMESPACE", MAIN)
    monkeypatch.setenv("TEMPORAL_QUEUE_NAMESPACES", MAPPING)
    get_worker_settings.cache_clear()
    yield
    get_worker_settings.cache_clear()


@pytest.fixture
def single_namespace(monkeypatch):
    monkeypatch.delenv("TEMPORAL_QUEUE_NAMESPACES", raising=False)
    monkeypatch.setenv("TEMPORAL_NAMESPACE", MAIN)
    get_worker_settings.cache_clear()
    yield
    get_worker_settings.cache_clear()


# --- mapping -----------------------------------------------------------------


def test_unset_mapping_keeps_every_queue_in_the_main_namespace(single_namespace):
    for queue in ("computor-tasks", "support", "coder-tasks", "testing", "testing-matlab"):
        assert namespace_for_queue(queue) == MAIN
    assert configured_namespaces() == [MAIN]


def test_mapping_routes_execution_queues(split_namespaces):
    assert namespace_for_queue("coder-tasks") == CODER_NS
    assert namespace_for_queue("testing") == GRADING_NS
    assert namespace_for_queue("testing-matlab") == GRADING_NS
    assert namespace_for_queue("computor-tasks") == MAIN
    assert namespace_for_queue("support") == MAIN
    # Main first, so an execution namespace can never shadow a control workflow id.
    assert configured_namespaces() == [MAIN, CODER_NS, GRADING_NS]


@pytest.mark.parametrize("value", ["testing", "=ns", "testing=", "computor-*=x", "*=x", "support=x"])
def test_malformed_or_control_queue_mappings_are_refused(value):
    with pytest.raises(ValueError):
        parse_queue_namespaces(value)


@pytest.mark.asyncio
async def test_namespace_clients_share_the_main_connection(split_namespaces):
    main = MagicMock()
    main.namespace = MAIN
    with patch.object(temporal_client, "_client", main), \
            patch.dict(temporal_client._namespace_clients, {}, clear=True):
        assert await get_temporal_client() is main
        assert await get_temporal_client(MAIN) is main
        coder = await get_temporal_client(CODER_NS)
        assert coder.namespace == CODER_NS
        assert coder.service_client is main.service_client
        assert await get_temporal_client(CODER_NS) is coder


# --- executor routing (mocked clients) ---------------------------------------


def _clients():
    clients = {}
    for ns in (MAIN, CODER_NS, GRADING_NS):
        c = MagicMock()
        c.namespace = ns
        c.start_workflow = AsyncMock()
        clients[ns] = c
    return clients


@pytest.mark.asyncio
async def test_submit_starts_testing_workflows_in_the_grading_namespace(split_namespaces):
    clients = _clients()

    async def fake_get(namespace=None):
        return clients[namespace or MAIN]

    import_task_modules()
    with patch("computor_backend.tasks.temporal_executor.get_temporal_client", side_effect=fake_get):
        await TemporalTaskExecutor().submit_task(TaskSubmission(
            task_name="student_testing", parameters={}, queue="testing", workflow_id="t-1",
        ))
        await TemporalTaskExecutor().submit_task(TaskSubmission(
            task_name="support_mail_import", parameters={}, queue="support",
        ))
    clients[GRADING_NS].start_workflow.assert_awaited_once()
    assert clients[GRADING_NS].start_workflow.call_args.kwargs["task_queue"] == "testing"
    clients[MAIN].start_workflow.assert_awaited_once()
    clients[CODER_NS].start_workflow.assert_not_awaited()


@pytest.mark.asyncio
async def test_lookup_falls_through_not_found_but_not_other_errors(split_namespaces):
    clients = _clients()
    not_found = RPCError("nf", RPCStatusCode.NOT_FOUND, b"")
    for ns in (MAIN, CODER_NS):
        clients[ns].get_workflow_handle.return_value.describe = AsyncMock(side_effect=not_found)
    found = MagicMock()
    clients[GRADING_NS].get_workflow_handle.return_value.describe = AsyncMock(return_value=found)

    async def fake_get(namespace=None):
        return clients[namespace or MAIN]

    with patch("computor_backend.tasks.temporal_executor.get_temporal_client", side_effect=fake_get):
        client, _handle, description = await TemporalTaskExecutor()._locate("x")
        assert client is clients[GRADING_NS] and description is found

        clients[GRADING_NS].get_workflow_handle.return_value.describe = AsyncMock(side_effect=not_found)
        with pytest.raises(TaskNotFoundError):
            await TemporalTaskExecutor()._locate("x")

        # An outage in one namespace is not "not found".
        clients[CODER_NS].get_workflow_handle.return_value.describe = AsyncMock(
            side_effect=RPCError("down", RPCStatusCode.UNAVAILABLE, b"")
        )
        with pytest.raises(RPCError):
            await TemporalTaskExecutor()._locate("x")


# --- integration on a dev server ----------------------------------------------


@workflow.defn(name="ns_probe", sandboxed=False)
class _ProbeWorkflow:
    @workflow.run
    async def run(self, value: str) -> str:
        return f"ran in {workflow.info().namespace}: {value}"


async def _start_env():
    return await WorkflowEnvironment.start_local(
        namespace=MAIN,
        dev_server_extra_args=["--namespace", CODER_NS, "--namespace", GRADING_NS],
    )


def _use_env_client(monkeypatch, env):
    monkeypatch.setattr(temporal_client, "_client", env.client)
    monkeypatch.setattr(temporal_client, "_namespace_clients", {})


def test_executor_round_trip_across_namespaces(split_namespaces, monkeypatch):
    async def scenario():
        env = await _start_env()
        try:
            _use_env_client(monkeypatch, env)
            grading = await get_temporal_client(GRADING_NS)
            executor = TemporalTaskExecutor()
            async with Worker(grading, task_queue="testing", workflows=[_ProbeWorkflow]):
                wf_id = f"probe-{uuid.uuid4()}"
                handle = await (await get_temporal_client(namespace_for_queue("testing"))).start_workflow(
                    "ns_probe", "x", id=wf_id, task_queue="testing",
                )
                assert await handle.result() == f"ran in {GRADING_NS}: x"
                info = await executor.get_task_status(wf_id)
                assert info.status == TaskStatus.FINISHED and info.queue == "testing"
                listed = await executor.list_tasks(limit=50)
                assert wf_id in {row["workflow_id"] for row in listed["tasks"]}
                # Not visible in the main namespace itself.
                with pytest.raises(RPCError) as err:
                    await env.client.get_workflow_handle(wf_id).describe()
                assert err.value.status == RPCStatusCode.NOT_FOUND
                with pytest.raises(TaskNotFoundError):
                    await executor.get_task_status(f"missing-{uuid.uuid4()}")
        finally:
            await env.shutdown()

    asyncio.run(scenario())


def test_exec_dispatch_activity_attaches_to_a_started_execution(split_namespaces, monkeypatch):
    """A retried run_exec_workflow waits for the first attempt's workflow."""

    async def scenario():
        env = await _start_env()
        try:
            _use_env_client(monkeypatch, env)
            import_task_modules()
            monkeypatch.setitem(task_registry._tasks, "ns_probe", setup.RolloutWorkspacesWorkflow)
            coder = await get_temporal_client(CODER_NS)
            async with Worker(coder, task_queue="coder-tasks", workflows=[_ProbeWorkflow]):
                wf_id = f"probe-{uuid.uuid4()}"
                act = ActivityEnvironment()
                first = await act.run(setup.run_exec_workflow, "ns_probe", wf_id, "a", "coder-tasks")
                again = await act.run(setup.run_exec_workflow, "ns_probe", wf_id, "b", "coder-tasks")
                assert first == again == f"ran in {CODER_NS}: a"
        finally:
            await env.shutdown()

    asyncio.run(scenario())


def test_rollout_control_applies_credentials_from_the_main_namespace(
    split_namespaces, monkeypatch, fake_coder  # noqa: F811
):
    async def scenario():
        env = await _start_env()
        try:
            _use_env_client(monkeypatch, env)
            import_task_modules()
            coder_client = await get_temporal_client(CODER_NS)
            with ThreadPoolExecutor(max_workers=4) as pool:
                coder_worker = Worker(
                    coder_client,
                    task_queue="coder-tasks",
                    workflows=task_registry.list_workflows(),
                    activities=task_registry.list_activities("coder-tasks"),
                    activity_executor=pool,
                )
                control = Worker(
                    env.client,
                    task_queue=setup.CONTROL_PLANE_TASK_QUEUE,
                    workflows=task_registry.list_workflows(),
                    activities=task_registry.list_activities(setup.CONTROL_PLANE_TASK_QUEUE),
                    activity_executor=pool,
                )
                async with coder_worker, control:
                    executor = TemporalTaskExecutor()
                    wf_id = await executor.submit_task(TaskSubmission(
                        task_name="rollout_workspaces_control",
                        parameters={"templates_dir": "/templates"},
                        queue=setup.CONTROL_PLANE_TASK_QUEUE,
                    ))
                    result = await asyncio.wait_for(executor.get_task_result(wf_id), 120)
                    info = await executor.get_task_status(wf_id)
                    exec_info = await executor.get_task_status(wf_id + setup.EXEC_WORKFLOW_ID_SUFFIX)
                    exec_history = await coder_client.get_workflow_handle(
                        wf_id + setup.EXEC_WORKFLOW_ID_SUFFIX
                    ).fetch_history()
            return result, info, exec_info, exec_history
        finally:
            await env.shutdown()

    result, info, exec_info, exec_history = asyncio.run(scenario())

    assert result.status == TaskStatus.FINISHED, result
    assert result.result["rollouts"][0]["updated_now"] == 2
    assert info.task_name == "rollout_workspaces"  # displayed under the known name
    assert info.progress["operation_status"] == "completed"
    assert exec_info.queue == "coder-tasks"
    applied = {ws for ws, _version, cred in fake_coder.updates if cred}
    assert applied == {"ws-alice-1", "ws-bob-1"}
    # The Coder namespace never scheduled the control-plane activity.
    scheduled = {
        e.activity_task_scheduled_event_attributes.activity_type.name
        for e in exec_history.events
        if e.HasField("activity_task_scheduled_event_attributes")
    }
    assert "apply_workspace_credential_updates" not in scheduled
    raw = b"".join(e.SerializeToString() for e in exec_history.events)
    assert b"argon2" not in raw
