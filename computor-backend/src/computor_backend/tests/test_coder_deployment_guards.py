"""Deployment guards in front of Coder template workflows and forced rollouts."""

import pytest

from computor_backend.api import coder as coder_api
from computor_backend.exceptions import ServiceUnavailableException


def test_public_deployment_requires_cgroup_parent(monkeypatch):
    monkeypatch.setenv("COMPUTOR_PUBLIC_DEPLOYMENT", "true")
    monkeypatch.delenv("CODER_WORKSPACE_CGROUP_PARENT", raising=False)
    with pytest.raises(ServiceUnavailableException):
        coder_api._require_public_workspace_limits()
    monkeypatch.setenv("CODER_WORKSPACE_CGROUP_PARENT", "computor-workspaces.slice")
    coder_api._require_public_workspace_limits()


def test_non_public_deployment_keeps_slice_optional(monkeypatch):
    monkeypatch.delenv("COMPUTOR_PUBLIC_DEPLOYMENT", raising=False)
    monkeypatch.delenv("CODER_WORKSPACE_CGROUP_PARENT", raising=False)
    coder_api._require_public_workspace_limits()
