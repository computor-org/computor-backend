"""Deployment guards in front of Coder template workflows and forced rollouts."""

import pytest

from computor_backend.api import coder as coder_api
from computor_backend.exceptions import ServiceUnavailableException


def test_public_deployment_requires_cgroup_parent(monkeypatch):
    monkeypatch.setenv("COMPUTOR_PUBLIC_DEPLOYMENT", "true")
    monkeypatch.setenv("CODER_MAX_RUNNING_WORKSPACES", "30")
    monkeypatch.delenv("CODER_WORKSPACE_CGROUP_PARENT", raising=False)
    with pytest.raises(ServiceUnavailableException):
        coder_api._require_public_workspace_limits()
    monkeypatch.setenv("CODER_WORKSPACE_CGROUP_PARENT", "computor-workspaces.slice")
    coder_api._require_public_workspace_limits()


def test_non_public_deployment_keeps_slice_optional(monkeypatch):
    monkeypatch.delenv("COMPUTOR_PUBLIC_DEPLOYMENT", raising=False)
    monkeypatch.delenv("CODER_WORKSPACE_CGROUP_PARENT", raising=False)
    coder_api._require_public_workspace_limits()


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value


class _FakeDb:
    def __init__(self, value):
        self.value = value
        self.params = None

    def execute(self, _statement, params):
        self.params = params
        return _FakeResult(self.value)


@pytest.mark.parametrize("value", [None, False])
def test_rollout_refused_without_worker_role(monkeypatch, value):
    monkeypatch.setenv("CODER_WORKER_DB_USER", "custom_worker")
    db = _FakeDb(value)
    with pytest.raises(ServiceUnavailableException):
        coder_api._require_worker_db_role(db)
    assert db.params == {"role": "custom_worker"}


def test_rollout_allowed_with_worker_role(monkeypatch):
    monkeypatch.delenv("CODER_WORKER_DB_USER", raising=False)
    db = _FakeDb(True)
    coder_api._require_worker_db_role(db)
    assert db.params == {"role": "computor_coder_worker"}


def test_workspace_size_caps_come_from_the_deployment(monkeypatch):
    monkeypatch.setenv("CODER_WORKSPACE_ROOTFS_SIZE", "10G")
    monkeypatch.setenv("CODER_WORKSPACE_TMP_SIZE", "512m")
    variables = coder_api._deployment_template_variables()
    assert variables["storage_size"] == "10G"
    assert variables["tmp_size"] == "512m"
    # Deployment-managed, so managers cannot override them per template.
    reasons = coder_api._locked_variable_reasons()
    assert "storage_size" in reasons and "tmp_size" in reasons
