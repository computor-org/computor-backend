"""Public deployments: the workspace slice's real limits gate push, rollout,
provisioning and start (fail closed)."""

import asyncio
import os
import uuid

import pytest

from computor_backend.api import coder as coder_api
from computor_backend.exceptions import ServiceUnavailableException
from computor_backend.tasks import temporal_coder_setup as setup
from computor_backend.tasks.worker_settings import get_worker_settings

LIMITED = "path=/a.slice/a-ws.slice\nmemory.max=2147483648\ncpu.max=300000 100000\npids.max=500\n"


@pytest.fixture(autouse=True)
def _fresh_worker_settings():
    """Settings are cached per process; these tests change the env."""
    get_worker_settings.cache_clear()
    yield
    get_worker_settings.cache_clear()


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


@pytest.mark.parametrize(
    "parent, path",
    [
        ("computor-workspaces.slice", "/computor.slice/computor-workspaces.slice"),
        ("a.slice", "/a.slice"),
        ("a-b-c.slice", "/a.slice/a-b.slice/a-b-c.slice"),
        ("/docker-ws", "/docker-ws"),
    ],
)
def test_slice_names_map_to_their_systemd_cgroup_path(parent, path):
    assert setup.slice_cgroup_path(parent) == path


@pytest.mark.parametrize(
    "parent", ["-.slice", "a--b.slice", "a-.slice", "../etc.slice", "/a/../../etc", "/", "computor"]
)
def test_unusable_parents_are_rejected(parent):
    assert setup.slice_cgroup_path(parent) is None


def _cgroup_tree(tmp_path, monkeypatch, limits=None):
    """A fake host cgroup2 root with computor-workspaces.slice below it."""
    (tmp_path / "cgroup.controllers").write_text("cpu memory pids\n")
    slice_dir = tmp_path / "computor.slice" / "computor-workspaces.slice"
    slice_dir.mkdir(parents=True)
    for name, value in (limits or {}).items():
        (slice_dir / name).write_text(value + "\n")
    monkeypatch.setenv("COMPUTOR_HOST_CGROUP_ROOT", str(tmp_path))
    return slice_dir


def test_limits_are_read_from_the_host_cgroup_tree(tmp_path, monkeypatch):
    _cgroup_tree(tmp_path, monkeypatch, {
        "memory.max": "2147483648", "cpu.max": "300000 100000", "pids.max": "500",
    })
    result = setup.verify_workspace_slice_limits("computor-workspaces.slice")
    assert result["success"], result
    assert result["limits"]["pids.max"] == "500"
    assert result["limits"]["path"] == "/computor.slice/computor-workspaces.slice"


def test_unlimited_slice_in_the_host_tree_is_refused(tmp_path, monkeypatch):
    _cgroup_tree(tmp_path, monkeypatch, {
        "memory.max": "max", "cpu.max": "max 100000", "pids.max": "max",
    })
    result = setup.verify_workspace_slice_limits("computor-workspaces.slice")
    assert not result["success"] and "pids.max is 'max'" in result["error"]


def test_inactive_slice_is_refused(tmp_path, monkeypatch):
    _cgroup_tree(tmp_path, monkeypatch)
    result = setup.verify_workspace_slice_limits("other-workspaces.slice")
    assert not result["success"] and "not active" in result["error"]


def test_missing_cgroup_mount_is_refused(tmp_path, monkeypatch):
    monkeypatch.setenv("COMPUTOR_HOST_CGROUP_ROOT", str(tmp_path / "absent"))
    result = setup.verify_workspace_slice_limits("computor-workspaces.slice")
    assert not result["success"] and "not mounted" in result["error"]


@pytest.mark.skipif(
    not os.path.isfile("/sys/fs/cgroup/cgroup.controllers"),
    reason="needs a cgroup2 host",
)
def test_real_unconfigured_slice_is_refused(monkeypatch):
    # A slice nothing has created has no cgroup; one Docker created on the fly
    # has no limits. Either way it must be refused.
    monkeypatch.setenv("COMPUTOR_HOST_CGROUP_ROOT", "/sys/fs/cgroup")
    result = setup.verify_workspace_slice_limits(f"wshtest{uuid.uuid4().hex[:6]}-ws.slice")
    assert not result["success"], result


@pytest.mark.skipif(
    not os.environ.get("COMPUTOR_TEST_LIMITED_SLICE"),
    reason="set COMPUTOR_TEST_LIMITED_SLICE to an active slice with MemoryMax/CPUQuota/TasksMax",
)
def test_real_limited_slice_is_accepted(monkeypatch):
    monkeypatch.setenv("COMPUTOR_HOST_CGROUP_ROOT", "/sys/fs/cgroup")
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
