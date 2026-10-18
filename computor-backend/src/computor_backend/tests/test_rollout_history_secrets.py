"""Workspace app credentials never enter Temporal history (#421).

Runs the real rollout_workspaces workflow on a local Temporal dev server
(``WorkflowEnvironment.start_local``; the SDK downloads the server on first
use) with the coder-tasks and control-plane workers registered from the task
registry, as temporal_worker does. Coder and the database are faked; the
credential derivation (HMAC from TOKEN_SECRET, Argon2 hash) is the real one.
The test then fetches the workflow history and checks that neither the secret
nor its bearer-equivalent hash appears in any event, while the workspace
identifiers do (so the search sees the payloads in plaintext).
"""

import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from computor_backend.tasks import temporal_coder_setup as setup
from computor_backend.tasks.registry import import_task_modules, task_registry

CODER_QUEUE = "coder-tasks"


class _FakeCoder:
    def __init__(self, workspaces):
        self.workspaces = workspaces
        self.updates = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get_template_active_version(self, name):
        return "version-2"

    async def list_all_workspaces(self):
        return self.workspaces

    async def set_workspace_auto_update(self, workspace_id, enabled):
        return True

    async def update_workspace_to_version(self, workspace_id, version_id, credentials=None):
        self.updates.append((workspace_id, version_id, credentials))
        return True


def _running(ws_id, owner):
    return SimpleNamespace(
        id=ws_id, name=f"name-{ws_id}", owner_name=owner, template_name="vscode-ws",
        template_version_id="version-1", latest_build_transition="start",
        latest_build_status=SimpleNamespace(value="running"),
    )


@pytest.fixture
def fake_coder(monkeypatch):
    import contextlib

    from computor_backend import database
    from computor_backend.coder import client as coder_client
    from computor_backend.coder import service

    fake = _FakeCoder([_running("ws-alice-1", "owner-alice"), _running("ws-bob-1", "owner-bob")])
    monkeypatch.setenv("TOKEN_SECRET", "history-test-token-secret")
    monkeypatch.setattr(coder_client, "CoderClient", lambda *a, **k: fake)
    monkeypatch.setattr(setup, "public_slice_error", lambda: None)
    monkeypatch.setattr(
        setup, "_discover_templates",
        lambda _dir: {"vscode": {"coder_template_name": "vscode-ws", "dir_name": "vscode"}},
    )
    monkeypatch.setattr(database, "get_db_session", lambda: contextlib.nullcontext(object()))
    # Real derivation; only the user lookup and key version are faked.
    monkeypatch.setattr(service, "workspace_app_key_version", lambda db, user_id: 1)
    monkeypatch.setattr(
        service, "workspace_app_credentials_for_owner",
        lambda db, owner: service.current_workspace_app_credentials(db, "uid-" + owner),
    )
    return fake


async def _run_rollout_and_fetch_history():
    import_task_modules()
    env = await WorkflowEnvironment.start_local()
    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            coder_worker = Worker(
                env.client,
                task_queue=CODER_QUEUE,
                workflows=[setup.RolloutWorkspacesWorkflow],
                activities=task_registry.list_activities(CODER_QUEUE),
                activity_executor=executor,
            )
            control_plane = Worker(
                env.client,
                task_queue=setup.CONTROL_PLANE_TASK_QUEUE,
                activities=task_registry.list_activities(setup.CONTROL_PLANE_TASK_QUEUE),
                activity_executor=executor,
            )
            async with coder_worker, control_plane:
                handle = await env.client.start_workflow(
                    setup.RolloutWorkspacesWorkflow.run,
                    {"templates_dir": "/templates"},
                    id=f"rollout-history-{uuid.uuid4()}",
                    task_queue=CODER_QUEUE,
                )
                result = await handle.result()
                history = await handle.fetch_history()
        return result, history
    finally:
        await env.shutdown()


def test_rollout_history_holds_no_workspace_credentials(fake_coder):
    result, history = asyncio.run(_run_rollout_and_fetch_history())

    assert result.status == "completed", result
    rollout = result.result["rollouts"][0]
    assert rollout["updated_now"] == 2, rollout

    # The control plane applied real credentials ...
    applied = {ws: cred for ws, _version, cred in fake_coder.updates}
    assert set(applied) == {"ws-alice-1", "ws-bob-1"}
    secrets = [c[0] for c in applied.values()] + [c[1] for c in applied.values()]
    assert all(c and c[1].startswith("$argon2") for c in applied.values())

    # ... and none of it is in the history, raw protobuf or JSON export.
    raw = b"".join(event.SerializeToString() for event in history.events)
    exported = history.to_json()
    for value in secrets:
        assert value.encode() not in raw
        assert value not in exported
    assert b"argon2" not in raw

    # Positive control: identifiers the activities exchanged are visible.
    assert b"ws-alice-1" in raw and b"owner-bob" in raw
    scheduled = [
        e.activity_task_scheduled_event_attributes
        for e in history.events
        if e.HasField("activity_task_scheduled_event_attributes")
    ]
    assert {(s.activity_type.name, s.task_queue.name) for s in scheduled} >= {
        ("rollout_template_workspaces", CODER_QUEUE),
        ("apply_workspace_credential_updates", setup.CONTROL_PLANE_TASK_QUEUE),
    }
