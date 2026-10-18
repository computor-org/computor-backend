"""Execution-host services run with least privilege (#421).

The compose half renders ops/docker the way the split worker host does
(base + prod + coder + workerhost) and the single-host way, and checks the
security settings that reach Docker. The workflow half checks that the coder
worker gets workspace credentials from the control plane and never derives
them itself (no TOKEN_SECRET, no database on the execution host).
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


def test_ingress_is_unprivileged_and_immutable(services):
    ingress = services["workspace-ingress"]
    assert ingress["user"] == "65534:65534"
    assert ingress["cap_drop"] == ["ALL"]
    assert ingress["read_only"] is True
    assert "no-new-privileges:true" in ingress["security_opt"]
    assert all(v.get("read_only") for v in ingress["volumes"])


@pytest.mark.parametrize("name", ["coder-socket-proxy", "coder-worker-socket-proxy"])
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


# --- credentials come from the control plane ---------------------------------


def test_control_plane_queue_is_the_default_worker_queue():
    assert setup.CONTROL_PLANE_TASK_QUEUE == DEFAULT_TASK_QUEUE
    names = {getattr(a, "__temporal_activity_definition").name for a in setup.ACTIVITIES}
    assert {"list_template_workspace_owners", "resolve_workspace_app_credentials"} <= names


def test_resolve_credentials_uses_the_database(monkeypatch):
    import contextlib

    from computor_backend import database
    from computor_backend.coder import service

    db = object()
    monkeypatch.setattr(database, "get_db_session", lambda: contextlib.nullcontext(db))
    monkeypatch.setattr(
        service, "workspace_app_credentials_for_owner",
        lambda session, owner: ("s-" + owner, "h-" + owner) if session is db and owner != "admin" else None,
    )
    assert setup.resolve_workspace_app_credentials(["ualice", "admin"]) == {
        "ualice": ["s-ualice", "h-ualice"],
        "admin": None,
    }


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


def test_rollout_applies_the_supplied_credentials_without_the_database(coder):
    result = asyncio.run(setup.rollout_template_workspaces(
        "vscode", "/t", True, {"ualice": ["sa", "ha"], "ubob": None},
    ))
    assert result["success"], result
    assert coder.updates == [("w1", "v2", ("sa", "ha")), ("w2", "v2", None)]


def test_owner_listing_is_per_template(coder):
    assert asyncio.run(setup.list_template_workspace_owners("vscode", "/t")) == ["ualice", "ubob"]
    assert asyncio.run(setup.list_template_workspace_owners("unknown", "/t")) == []


def _run_workflow(monkeypatch, fail_resolve=False, patched=True):
    from temporalio.exceptions import ActivityError, ApplicationError, RetryState

    calls = []

    async def execute_activity(fn, args=None, task_queue=None, **kwargs):
        name = fn.__temporal_activity_definition.name
        calls.append((name, task_queue, args))
        if name == "discover_template_operations":
            return [{"dir_name": "vscode", "coder_template_name": "vscode-ws"}]
        if name == "list_template_workspace_owners":
            return ["ualice"]
        if name == "resolve_workspace_app_credentials":
            if fail_resolve:
                raise ActivityError(
                    "failed", scheduled_event_id=1, started_event_id=2, identity="t",
                    activity_type=name, activity_id="1", retry_state=RetryState.MAXIMUM_ATTEMPTS_REACHED,
                ) from ApplicationError("not registered")
            return {"ualice": ["s", "h"]}
        if name == "rollout_template_workspaces":
            return {"success": True, "template": "vscode-ws", "errors": []}
        raise AssertionError(name)

    monkeypatch.setattr(setup.workflow, "execute_activity", execute_activity)
    monkeypatch.setattr(setup.workflow, "patched", lambda patch_id: patched)
    result = asyncio.run(setup.RolloutWorkspacesWorkflow().run({"templates_dir": "/t"}))
    return result, calls


def test_workflow_resolves_credentials_on_the_control_plane(monkeypatch):
    result, calls = _run_workflow(monkeypatch)
    assert result.status == "completed", result
    assert [c[:2] for c in calls] == [
        ("discover_template_operations", None),
        ("list_template_workspace_owners", None),  # coder worker
        ("resolve_workspace_app_credentials", DEFAULT_TASK_QUEUE),  # control plane
        ("rollout_template_workspaces", None),
    ]
    assert calls[-1][2] == ["vscode", "/t", True, {"ualice": ["s", "h"]}]


def test_workflow_fails_the_template_when_credentials_cannot_be_resolved(monkeypatch):
    result, calls = _run_workflow(monkeypatch, fail_resolve=True)
    assert result.status == "completed_with_errors"
    assert "rollout_template_workspaces" not in [c[0] for c in calls]
    assert "could not resolve workspace credentials" in result.result["rollouts"][0]["error"]


def test_workflow_replays_old_histories_without_the_lookup(monkeypatch):
    _, calls = _run_workflow(monkeypatch, patched=False)
    assert [c[0] for c in calls] == ["discover_template_operations", "rollout_template_workspaces"]
    assert calls[-1][2] == ["vscode", "/t"]
