"""Template-centric Coder fleet readiness and operation locking."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from computor_backend.api.coder import (
    _reject_conflicting_coder_task,
    get_workspace_fleet_status,
)
from computor_backend.coder.schemas import (
    CoderTemplate,
    CoderWorkspace,
    WorkspaceBuildStatus,
)
from computor_backend.exceptions import ConflictException
from computor_backend.permissions.principal import Principal


def _admin() -> Principal:
    return Principal(user_id="admin", roles=["_admin"])


@pytest.mark.asyncio
async def test_fleet_status_distinguishes_actionable_and_scheduled_workspaces():
    client = MagicMock()
    client.health_check = AsyncMock(return_value=(True, "2.29.4"))
    client.list_templates = AsyncMock(return_value=[
        CoderTemplate(id="t1", name="vscode-workspace", display_name="VS Code", active_version_id="v2"),
        CoderTemplate(id="t2", name="bash-workspace", display_name="Bash", active_version_id=None),
    ])
    client.list_all_workspaces = AsyncMock(return_value=[
        CoderWorkspace(
            id="current", name="current", owner_id="u1", template_id="t1",
            template_version_id="v2", latest_build_transition="stop",
            latest_build_status=WorkspaceBuildStatus.STOPPED, automatic_updates="never",
        ),
        CoderWorkspace(
            id="running", name="running", owner_id="u1", template_id="t1",
            template_version_id="v1", latest_build_transition="start",
            latest_build_status=WorkspaceBuildStatus.SUCCEEDED, automatic_updates="always",
        ),
        CoderWorkspace(
            id="scheduled", name="scheduled", owner_id="u2", template_id="t1",
            template_version_id="v1", latest_build_transition="stop",
            latest_build_status=WorkspaceBuildStatus.STOPPED, automatic_updates="always",
        ),
        CoderWorkspace(
            id="actionable", name="actionable", owner_id="u3", template_id="t1",
            template_version_id="v1", latest_build_transition="stop",
            latest_build_status=WorkspaceBuildStatus.STOPPED, automatic_updates="never",
        ),
    ])

    response = await get_workspace_fleet_status(_admin(), MagicMock(), client)

    vscode = response.templates[0]
    assert response.version == "2.29.4"
    assert vscode.workspace_count == 4
    assert vscode.current_count == 1
    assert vscode.outdated_count == 3
    assert vscode.running_outdated_count == 1
    assert vscode.scheduled_on_start_count == 1
    assert vscode.actionable_count == 2
    assert vscode.rollout_state == "ready"
    assert response.templates[1].rollout_state == "unavailable"


@pytest.mark.asyncio
async def test_active_coder_operation_rejects_conflicting_submission():
    executor = MagicMock()
    executor.list_tasks = AsyncMock(return_value={"tasks": [{
        "task_id": "push-1",
        "workflow_id": "push-1",
        "task_name": "push_coder_templates",
        "status": "started",
    }]})
    with patch(
        "computor_backend.api.coder.get_task_executor",
        return_value=executor,
    ):
        with pytest.raises(ConflictException, match="already running"):
            await _reject_conflicting_coder_task()
