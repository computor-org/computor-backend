"""Public deployments: the workspace slice's real limits gate push, rollout,
provisioning and start (fail closed)."""

import asyncio
import os
import shutil
import uuid

import pytest

from computor_backend.api import coder as coder_api
from computor_backend.exceptions import ServiceUnavailableException
from computor_backend.tasks import temporal_coder_setup as setup

LIMITED = "path=/a.slice/a-ws.slice\nmemory.max=2147483648\ncpu.max=300000 100000\npids.max=500\n"


def test_parse_accepts_fully_limited_slice():
    assert setup.parse_slice_limits(LIMITED)["success"]


@pytest.mark.parametrize(
    "output",
    [
        "path=/a.slice/a-ws.slice\nmemory.max=max\ncpu.max=max 100000\npids.max=max\n",
        LIMITED.replace("pids.max=500", "pids.max=max"),
        LIMITED.replace("memory.max=2147483648", "memory.max=missing"),
        LIMITED.replace("cpu.max=300000 100000", "cpu.max=max 100000"),
        LIMITED.replace("path=/a.slice/a-ws.slice", "path=/"),
        "",
    ],
)
def test_parse_fails_closed(output):
    result = setup.parse_slice_limits(output)
    assert not result["success"] and result["error"]


def test_missing_parent_is_refused(monkeypatch):
    monkeypatch.delenv("CODER_WORKSPACE_CGROUP_PARENT", raising=False)
    assert not setup.verify_workspace_slice_limits()["success"]


@pytest.mark.skipif(
    not os.path.exists("/var/run/docker.sock") or shutil.which("docker") is None,
    reason="needs a local docker daemon",
)
def test_real_unconfigured_slice_is_refused(monkeypatch):
    # Docker creates an unknown slice on the fly with no limits at all.
    monkeypatch.setenv("DOCKER_SOCKET_PATH", "/var/run/docker.sock")
    result = setup.verify_workspace_slice_limits(f"wshtest{uuid.uuid4().hex[:6]}-ws.slice")
    assert not result["success"], result


@pytest.mark.skipif(
    not os.environ.get("COMPUTOR_TEST_LIMITED_SLICE"),
    reason="set COMPUTOR_TEST_LIMITED_SLICE to a slice with MemoryMax/CPUQuota/TasksMax",
)
def test_real_limited_slice_is_accepted():
    result = setup.verify_workspace_slice_limits(os.environ["COMPUTOR_TEST_LIMITED_SLICE"])
    assert result["success"], result


def test_worker_push_and_rollout_refuse_unverified_slice(monkeypatch):
    monkeypatch.setenv("COMPUTOR_PUBLIC_DEPLOYMENT", "true")
    monkeypatch.setattr(
        setup, "verify_workspace_slice_limits",
        lambda *a, **k: {"success": False, "error": "pids.max is 'max'"},
    )
    monkeypatch.setattr(setup, "_discover_templates", lambda *_: pytest.fail("must not get here"))
    push = asyncio.run(setup.push_coder_template(
        "vscode", "/nonexistent", "http://coder", "a@b", "pw", "http://i", "http://e", "", 1, 1,
    ))
    rollout = asyncio.run(setup.rollout_template_workspaces("vscode", "/nonexistent"))
    for result in (push, rollout):
        assert not result["success"] and "pids.max" in result["error"]


@pytest.fixture
def public(monkeypatch):
    monkeypatch.setenv("COMPUTOR_PUBLIC_DEPLOYMENT", "true")
    monkeypatch.setenv("CODER_MAX_RUNNING_WORKSPACES", "30")
    monkeypatch.setenv("CODER_WORKSPACE_CGROUP_PARENT", "computor-workspaces.slice")
    monkeypatch.setattr(coder_api, "_SLICE_VERIFIED_AT", None)


def test_api_gate_fails_closed_and_caches_success(public, monkeypatch):
    calls = []

    async def failing(action, volume=None):
        calls.append(action)
        raise RuntimeError("worker unreachable")

    monkeypatch.setattr(coder_api, "_run_volume_task", failing)
    with pytest.raises(ServiceUnavailableException):
        asyncio.run(coder_api._require_verified_workspace_limits())

    async def ok(action, volume=None):
        calls.append(action)
        return {"success": True}

    monkeypatch.setattr(coder_api, "_run_volume_task", ok)
    asyncio.run(coder_api._require_verified_workspace_limits())
    asyncio.run(coder_api._require_verified_workspace_limits())
    assert calls == ["verify_slice", "verify_slice"]


def test_api_gate_is_noop_when_not_public(monkeypatch):
    monkeypatch.delenv("COMPUTOR_PUBLIC_DEPLOYMENT", raising=False)
    monkeypatch.setattr(coder_api, "_run_volume_task", lambda *a, **k: pytest.fail("no check"))
    asyncio.run(coder_api._require_verified_workspace_limits())


def _refuse(monkeypatch):
    async def failing(action, volume=None):
        raise RuntimeError("pids.max is 'max'")

    monkeypatch.setattr(coder_api, "_run_volume_task", failing)


def test_start_endpoint_is_gated(public, monkeypatch):
    _refuse(monkeypatch)
    monkeypatch.setattr(coder_api, "_check_workspace_access_or_course_member", lambda *a, **k: None)
    with pytest.raises(ServiceUnavailableException):
        asyncio.run(coder_api.start_workspace("u", "w", object(), object(), object(), object()))


def test_rollout_endpoint_is_gated(public, monkeypatch):
    _refuse(monkeypatch)
    monkeypatch.setattr(coder_api, "_check_workspace_access", lambda *a, **k: None)
    monkeypatch.setattr(coder_api, "_require_worker_db_role", lambda *a, **k: None)
    with pytest.raises(ServiceUnavailableException):
        asyncio.run(coder_api.rollout_workspaces_endpoint(object(), object(), object(), object()))


def test_push_endpoint_is_gated(public, monkeypatch):
    _refuse(monkeypatch)
    monkeypatch.setattr(coder_api, "_check_workspace_access", lambda *a, **k: None)
    with pytest.raises(ServiceUnavailableException):
        asyncio.run(coder_api.push_coder_templates(object(), object(), object(), object()))
