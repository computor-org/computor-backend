"""Workspace volume activities: what they refuse, and what they report.

These run on the coder worker because only it has Docker access; the tests
drive the plain functions with a faked docker client and host spool.
"""

from unittest.mock import MagicMock, patch

import pytest

from computor_backend.tasks.temporal_coder_setup import (
    delete_workspace_volume,
    list_workspace_volumes,
    repair_volume_ownership,
)


def _docker(df_payload=None, **client_attrs):
    client = MagicMock()
    client.api._result.return_value = df_payload or {"Volumes": []}
    for k, v in client_attrs.items():
        setattr(client, k, v)
    return client


def _patch(client):
    return patch("docker.DockerClient", return_value=client)


# --- listing ------------------------------------------------------------------


def test_only_workspace_volumes_are_reported():
    """The daemon hosts the whole platform's volumes; postgres and minio data
    are not ours to offer for deletion."""
    client = _docker({"Volumes": [
        {"Name": "coder-home-abc", "UsageData": {"Size": 100, "RefCount": 0}},
        {"Name": "coder-scratch-xyz", "UsageData": {"Size": 200, "RefCount": 1}},
        {"Name": "computor_postgres-data", "UsageData": {"Size": 999, "RefCount": 1}},
    ]})
    with _patch(client):
        result = list_workspace_volumes()
    assert result["success"] is True
    assert [v["name"] for v in result["volumes"]] == ["coder-home-abc", "coder-scratch-xyz"]
    assert [v["kind"] for v in result["volumes"]] == ["home", "scratch"]
    assert result["volumes"][1]["in_use"] is True


def test_an_uncomputed_size_is_reported_as_unknown():
    """Docker returns -1 when it has not measured a volume. Reporting that as
    0 B would read as "empty, safe to delete"."""
    client = _docker({"Volumes": [
        {"Name": "coder-home-abc", "UsageData": {"Size": -1, "RefCount": 0}},
    ]})
    with _patch(client):
        volume = list_workspace_volumes()["volumes"][0]
    assert volume["size_bytes"] is None


def test_listing_falls_back_when_the_daemon_rejects_the_type_filter():
    """The volume-only df needs docker API >= 1.42; older daemons get the full
    (slower) call rather than an error."""
    client = MagicMock()
    client.api._result.side_effect = Exception("unsupported")
    client.df.return_value = {"Volumes": [
        {"Name": "coder-home-abc", "UsageData": {"Size": 5, "RefCount": 0}},
    ]}
    with _patch(client):
        result = list_workspace_volumes()
    assert result["success"] is True
    assert result["volumes"][0]["size_bytes"] == 5


def test_a_docker_failure_is_reported_not_raised():
    client = MagicMock()
    client.api._result.side_effect = Exception("boom")
    client.df.side_effect = Exception("boom")
    with _patch(client):
        result = list_workspace_volumes()
    assert result["success"] is False and result["volumes"] == []


# --- delete / repair guards ---------------------------------------------------


@pytest.mark.parametrize("action", [delete_workspace_volume, repair_volume_ownership])
def test_non_workspace_volumes_are_refused(action):
    """Name-prefix check first, before touching docker at all: these actions
    are destructive and the caller supplies the name."""
    client = _docker()
    with _patch(client):
        result = action("computor_postgres-data")
    assert result["success"] is False
    assert "not a workspace volume" in result["error"]
    client.volumes.get.assert_not_called()
    client.containers.run.assert_not_called()


def test_a_volume_in_use_is_refused_with_a_usable_message():
    """Docker 409s rather than yanking a mounted volume, and that is the
    behaviour we want surfaced — forcing it would pull the home out from under
    a running workspace."""
    client = _docker()
    client.volumes.get.return_value.remove.side_effect = Exception(
        "409 Client Error: volume is in use"
    )
    with _patch(client):
        result = delete_workspace_volume("coder-home-abc")
    assert result["success"] is False
    assert "stop the workspace first" in result["error"]


def test_repair_is_handed_to_the_host_not_run_as_a_container():
    """The worker's Docker proxy refuses container create, so the chown is a
    host request; nothing goes through the docker client."""
    client = _docker()
    sent = {}

    def submit(action, fields, timeout, heartbeat=None):
        sent["action"], sent["fields"] = action, fields
        return {"status": "ok", "message": "done"}

    with _patch(client), patch(
        "computor_backend.tasks.temporal_coder_setup.coder_hostops.submit", submit
    ):
        result = repair_volume_ownership("coder-home-abc")
    assert result["success"] is True
    assert sent == {"action": "chown-volume", "fields": [("volume", "coder-home-abc")]}
    client.containers.run.assert_not_called()


def test_repair_reports_a_host_failure():
    with patch(
        "computor_backend.tasks.temporal_coder_setup.coder_hostops.submit",
        lambda *a, **k: {"status": "error", "message": "host did not answer"},
    ):
        result = repair_volume_ownership("coder-home-abc")
    assert result == {"success": False, "error": "host did not answer"}
