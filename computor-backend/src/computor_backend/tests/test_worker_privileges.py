"""Execution-host services run with least privilege (#421).

The compose half renders ops/docker the way the split worker host does
(base + prod + coder + workerhost) and the single-host way, and checks the
security settings that reach Docker. The workflow half checks that running
workspaces are rebuilt with their credentials on the control plane, which is
the only worker that registers that activity (no TOKEN_SECRET, no database on
the execution host). test_rollout_history_secrets.py checks the Temporal
history on a real server.
"""

import asyncio
from types import SimpleNamespace

import pytest

from computor_backend.tasks import temporal_coder_setup as setup
from computor_backend.tasks.temporal_client import DEFAULT_TASK_QUEUE
from computor_backend.tests.test_coder_worker_docker_compose import _render


@pytest.fixture(params=[("base", "prod", "coder"), ("base", "prod", "coder", "workerhost")])
def services(request, tmp_path):
    return _render(tmp_path, request.param)["services"]


def test_coder_worker_is_unprivileged_and_immutable(services):
    worker = services["temporal-worker-coder"]
    assert worker["user"] == "1000:1000"
    assert worker["cap_drop"] == ["ALL"]
    assert "no-new-privileges:true" in worker["security_opt"]
    assert worker["read_only"] is True
    assert any(t.startswith("/tmp:") and "size=" in t for t in worker["tmpfs"])


def test_coder_worker_holds_no_control_plane_secret(services):
    env = services["temporal-worker-coder"]["environment"]
    for name in ("TOKEN_SECRET", "POSTGRES_PASSWORD", "POSTGRES_USER", "POSTGRES_HOST"):
        assert name not in env, name
    # What it still needs: Coder admin login, Temporal, the Docker proxy.
    assert {"CODER_ADMIN_PASSWORD", "TEMPORAL_HOST", "DOCKER_HOST"} <= set(env)


def test_control_plane_worker_can_reach_coder(services):
    # apply_workspace_credential_updates sends the update builds itself.
    env = services["temporal-worker"]["environment"]
    assert {"CODER_URL", "CODER_ADMIN_EMAIL", "CODER_ADMIN_PASSWORD", "TOKEN_SECRET"} <= set(env)


def test_ingress_is_unprivileged_and_immutable(services):
    ingress = services["workspace-ingress"]
    assert ingress["user"] == "65534:65534"
    assert ingress["cap_drop"] == ["ALL"]
    assert ingress["read_only"] is True
    assert "no-new-privileges:true" in ingress["security_opt"]
    assert all(v.get("read_only") for v in ingress["volumes"])


@pytest.mark.parametrize(
    "name", ["coder-socket-proxy", "coder-worker-socket-proxy", "coder-provisioner-socket-proxy"]
)
def test_socket_proxies_have_no_capabilities(services, name):
    proxy = services[name]
    assert proxy["cap_drop"] == ["ALL"]
    assert "no-new-privileges:true" in proxy["security_opt"]
    assert all(v.get("read_only") for v in proxy["volumes"])


def test_testing_worker_is_unprivileged(services):
    worker = services["temporal-worker-testing"]
    assert not worker["user"].startswith("0")
    assert worker["cap_drop"] == ["ALL"]
    assert "no-new-privileges:true" in worker["security_opt"]
    assert not worker.get("volumes")  # nothing from the host


# --- credentials are derived and applied on the control plane ----------------


def test_control_plane_queue_is_the_default_worker_queue():
    assert setup.CONTROL_PLANE_TASK_QUEUE == DEFAULT_TASK_QUEUE
    shared = {a.__temporal_activity_definition.name for a in setup.ACTIVITIES}
    assert "apply_workspace_credential_updates" not in shared
    assert setup.QUEUE_ACTIVITIES == {
        DEFAULT_TASK_QUEUE: [
            setup.apply_workspace_credential_updates,
            setup.run_exec_workflow,
        ],
    }


def _registered_names(task_queue):
    from computor_backend.tasks.registry import import_task_modules, task_registry

    import_task_modules()
    return {
        a.__temporal_activity_definition.name
        for a in task_registry.list_activities(task_queue)
    }


@pytest.mark.parametrize("queue", ["coder-tasks", "testing", "testing-matlab"])
def test_credential_update_is_absent_from_execution_workers(queue):
    names = _registered_names(queue)
    assert "rollout_template_workspaces" in names  # shared ones still there
    assert "apply_workspace_credential_updates" not in names
    assert "run_exec_workflow" not in names


def test_credential_update_is_registered_on_the_control_plane():
    assert "apply_workspace_credential_updates" in _registered_names(DEFAULT_TASK_QUEUE)


def test_temporal_worker_registers_per_queue(monkeypatch):
    """The real TemporalWorker.start hands each queue's Worker its own list."""
    from computor_backend.tasks import temporal_worker

    created = {}

    class _Worker:
        def __init__(self, client, *, task_queue, activities, **kwargs):
            created[task_queue] = {
                getattr(a, "__temporal_activity_definition").name for a in activities
            }

        async def run(self):
            return None

        async def shutdown(self):
            return None

    async def _client(namespace=None):
        return SimpleNamespace()

    monkeypatch.setattr(temporal_worker, "Worker", _Worker)
    monkeypatch.setattr(temporal_worker, "get_temporal_client", _client)
    worker = temporal_worker.TemporalWorker(
        task_queues=[DEFAULT_TASK_QUEUE, "coder-tasks", "testing"], heartbeat_interval=0
    )
    asyncio.run(worker.start())
    assert "apply_workspace_credential_updates" in created[DEFAULT_TASK_QUEUE]
    assert "apply_workspace_credential_updates" not in created["coder-tasks"]
    assert "apply_workspace_credential_updates" not in created["testing"]


class _FakeCoder:
    def __init__(self, workspaces):
        self.workspaces = workspaces
        self.updates = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get_template_active_version(self, name):
        return "v2"

    async def list_all_workspaces(self):
        return self.workspaces

    async def set_workspace_auto_update(self, workspace_id, enabled):
        return True

    async def update_workspace_to_version(self, workspace_id, version_id, credentials=None):
        self.updates.append((workspace_id, version_id, credentials))
        return True


def _running(ws_id, owner, template="vscode-ws"):
    return SimpleNamespace(
        id=ws_id, name=ws_id, owner_name=owner, template_name=template,
        template_version_id="v1", latest_build_transition="start",
        latest_build_status=SimpleNamespace(value="running"),
    )


@pytest.fixture
def coder(monkeypatch):
    from computor_backend import database
    from computor_backend.coder import client as coder_client

    fake = _FakeCoder([_running("w1", "ualice"), _running("w2", "ubob"),
                       _running("w3", "ucarol", template="other")])
    monkeypatch.setattr(coder_client, "CoderClient", lambda *a, **k: fake)
    monkeypatch.setattr(setup, "public_slice_error", lambda: None)
    monkeypatch.setattr(
        setup, "_discover_templates",
        lambda _dir: {"vscode": {"coder_template_name": "vscode-ws", "dir_name": "vscode"}},
    )
    # The execution host has no database: any use of it is a failure.
    monkeypatch.setattr(database, "get_db_session", lambda: pytest.fail("worker used the DB"))
    return fake


def test_deferred_rollout_lists_running_workspaces_without_rebuilding(coder):
    result = asyncio.run(setup.rollout_template_workspaces("vscode", "/t", True, True))
    assert result["success"], result
    assert coder.updates == []
    assert result["pending_updates"] == [
        {"id": "w1", "name": "w1", "owner_name": "ualice"},
        {"id": "w2", "name": "w2", "owner_name": "ubob"},
    ]
    assert result["active_version"] == "v2"


def test_legacy_rollout_rebuilds_with_the_existing_credential(coder):
    result = asyncio.run(setup.rollout_template_workspaces("vscode", "/t"))
    assert result["success"], result
    assert coder.updates == [("w1", "v2", None), ("w2", "v2", None)]
    assert result["pending_updates"] == []


def test_gentle_rollout_only_sets_auto_update(coder):
    result = asyncio.run(setup.rollout_template_workspaces("vscode", "/t", False, True))
    assert result["success"] and result["auto_update_on_start"] == 2, result
    assert coder.updates == [] and result["pending_updates"] == []


def test_control_plane_applies_current_credentials(monkeypatch, coder):
    import contextlib

    from computor_backend import database
    from computor_backend.coder import service

    db = object()
    monkeypatch.setattr(database, "get_db_session", lambda: contextlib.nullcontext(db))
    monkeypatch.setattr(
        service, "workspace_app_credentials_for_owner",
        lambda session, owner: ("s-" + owner, "h-" + owner) if session is db and owner != "admin" else None,
    )
    result = asyncio.run(setup.apply_workspace_credential_updates("v2", [
        {"id": "w1", "name": "w1", "owner_name": "ualice"},
        {"id": "w9", "name": "w9", "owner_name": "admin"},
    ]))
    assert result == {"updated_now": 2, "errors": []}
    assert coder.updates == [("w1", "v2", ("s-ualice", "h-ualice")), ("w9", "v2", None)]


def test_control_plane_setup_errors_carry_no_secret(monkeypatch, coder):
    """A settings error quoting the admin password must not reach Temporal history."""
    import contextlib

    from temporalio.exceptions import ApplicationError

    from computor_backend import database
    from computor_backend.coder import client as coder_client

    secret = "pw-SECRET-123"
    monkeypatch.setattr(database, "get_db_session", lambda: contextlib.nullcontext(object()))

    def broken_client(*args, **kwargs):
        raise ValueError(f"CODER_ADMIN_EMAIL missing; CODER_ADMIN_PASSWORD={secret}")

    monkeypatch.setattr(coder_client, "CoderClient", broken_client)
    with pytest.raises(ApplicationError) as raised:
        asyncio.run(setup.apply_workspace_credential_updates("v2", [
            {"id": "w1", "name": "w1", "owner_name": "ualice"}]))
    error = raised.value
    assert error.message == "credential update failed (ValueError)"
    assert secret not in str(error) and secret not in repr(error.details)
    assert error.__cause__ is None and error.__context__ is None


def _run_workflow(monkeypatch, fail_apply=False, patched=True, pending=True):
    from temporalio.exceptions import ActivityError, ApplicationError, RetryState

    calls = []

    async def execute_activity(fn, args=None, task_queue=None, **kwargs):
        name = fn.__temporal_activity_definition.name
        calls.append((name, task_queue, args))
        if name == "discover_template_operations":
            return [{"dir_name": "vscode", "coder_template_name": "vscode-ws"}]
        if name == "rollout_template_workspaces":
            return {
                "success": True, "template": "vscode-ws", "active_version": "v2",
                "updated_now": 0, "errors": [],
                "pending_updates": [{"id": "w1", "name": "w1", "owner_name": "ualice"}]
                if pending else [],
            }
        if name == "apply_workspace_credential_updates":
            if fail_apply:
                raise ActivityError(
                    "failed", scheduled_event_id=1, started_event_id=2, identity="t",
                    activity_type=name, activity_id="1", retry_state=RetryState.TIMEOUT,
                ) from ApplicationError("no control-plane worker")
            return {"updated_now": 1, "errors": []}
        raise AssertionError(name)

    monkeypatch.setattr(setup.workflow, "execute_activity", execute_activity)
    monkeypatch.setattr(setup.workflow, "patched", lambda patch_id: patched)
    result = asyncio.run(setup.RolloutWorkspacesWorkflow().run({"templates_dir": "/t"}))
    return result, calls


def test_workflow_applies_credentials_on_the_control_plane(monkeypatch):
    result, calls = _run_workflow(monkeypatch)
    assert result.status == "completed", result
    assert [c[:2] for c in calls] == [
        ("discover_template_operations", None),
        ("rollout_template_workspaces", None),  # coder worker
        ("apply_workspace_credential_updates", DEFAULT_TASK_QUEUE),  # control plane
    ]
    assert calls[1][2] == ["vscode", "/t", True, True]
    assert calls[2][2] == ["v2", [{"id": "w1", "name": "w1", "owner_name": "ualice"}]]
    rollout = result.result["rollouts"][0]
    assert rollout["updated_now"] == 1 and "pending_updates" not in rollout


def test_workflow_skips_the_control_plane_without_running_workspaces(monkeypatch):
    result, calls = _run_workflow(monkeypatch, pending=False)
    assert result.status == "completed"
    assert "apply_workspace_credential_updates" not in [c[0] for c in calls]


def test_workflow_fails_the_template_when_the_control_plane_is_unavailable(monkeypatch):
    result, _ = _run_workflow(monkeypatch, fail_apply=True)
    assert result.status == "completed_with_errors"
    rollout = result.result["rollouts"][0]
    assert not rollout["success"]
    assert "could not update running workspaces on the control plane" in rollout["error"]


def test_workflow_replays_old_histories_without_the_deferral(monkeypatch):
    _, calls = _run_workflow(monkeypatch, patched=False)
    assert [c[0] for c in calls] == ["discover_template_operations", "rollout_template_workspaces"]
    assert calls[-1][2] == ["vscode", "/t"]
