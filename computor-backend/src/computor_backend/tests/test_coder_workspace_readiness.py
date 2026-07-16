"""Agent-lifecycle readiness on workspace details.

`status == RUNNING` only means the Terraform apply succeeded — the container
exists, but the service inside may still be booting. The web launch page sends
the user to the workspace on `ready`, so these tests pin down that `ready` means
"running AND the agent finished its startup script", not merely "running".
"""

from unittest.mock import MagicMock

from computor_backend.coder.client import CoderClient
from computor_backend.coder.schemas import WorkspaceStatus


def _client() -> CoderClient:
    client = CoderClient.__new__(CoderClient)  # bypass __init__ (needs real settings/http)
    client.settings = MagicMock()
    client.settings.workspace_base_url = "http://localhost:8080/coder"
    return client


def _payload(job_status: str, transition: str, lifecycle: str | None) -> dict:
    agent: dict = {"name": "main", "status": "connected"}
    if lifecycle is not None:
        agent["lifecycle_state"] = lifecycle
    return {
        "id": "ws1",
        "name": "vscode",
        "owner_id": "o1",
        "owner_name": "u123",
        "template_id": "t1",
        "latest_build": {
            "status": job_status,
            "transition": transition,
            "job": {"status": job_status},
            "resources": [{"name": "main", "agents": [agent]}],
        },
    }


def test_ready_when_running_and_agent_finished_startup_script():
    details = _client()._parse_workspace_details(_payload("succeeded", "start", "ready"))

    assert details.status == WorkspaceStatus.RUNNING
    assert details.agent_lifecycle == "ready"
    assert details.ready is True
    assert details.code_server_url == "http://localhost:8080/coder/u123/vscode/"


def test_not_ready_while_startup_script_still_running():
    # The 502 case: the build is done and the URL exists, but the service inside
    # is still coming up. Must not be reported ready.
    details = _client()._parse_workspace_details(_payload("succeeded", "start", "starting"))

    assert details.status == WorkspaceStatus.RUNNING
    assert details.agent_lifecycle == "starting"
    assert details.ready is False


def test_not_ready_while_build_still_running_even_if_agent_ready():
    details = _client()._parse_workspace_details(_payload("running", "start", "ready"))

    assert details.status == WorkspaceStatus.STARTING
    assert details.ready is False


def test_lifecycle_surfaced_when_startup_script_gave_up():
    # The web treats these as "stop waiting" rather than spinning forever.
    details = _client()._parse_workspace_details(_payload("succeeded", "start", "start_timeout"))

    assert details.agent_lifecycle == "start_timeout"
    assert details.ready is False


def test_missing_lifecycle_is_not_ready():
    # Older Coder payloads / agentless resources must not fake readiness.
    details = _client()._parse_workspace_details(_payload("succeeded", "start", None))

    assert details.agent_lifecycle is None
    assert details.ready is False


def test_lifecycle_also_exposed_on_resources():
    details = _client()._parse_workspace_details(_payload("succeeded", "start", "ready"))

    assert details.resources["main"]["lifecycle_state"] == "ready"
    # The pre-existing connection status must survive alongside it.
    assert details.resources["main"]["status"] == "connected"
