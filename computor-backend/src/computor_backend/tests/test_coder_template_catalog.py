"""The workspace template catalog.

Nothing is pushed to Coder automatically, so the catalog is the only thing that
makes an undeployed template reachable from the UI. The cases that matter are
the ones where disk and Coder disagree.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from computor_backend.api.coder import list_template_catalog
from computor_backend.coder import templates_fs
from computor_backend.coder.config import CoderSettings
from computor_backend.coder.schemas import (
    CoderTemplate,
    CoderWorkspace,
    WorkspaceBuildStatus,
)
from computor_backend.model.workspace import WorkspaceTemplateSettings
from computor_backend.permissions.principal import Principal


def _admin() -> Principal:
    return Principal(user_id="admin", roles=["_admin"])


def _settings(templates_dir: str) -> CoderSettings:
    return CoderSettings(
        admin_email="admin@example.com",
        admin_password="x",
        templates_dir=templates_dir,
    )


def _db(rows) -> MagicMock:
    db = MagicMock()
    db.query.return_value.all.return_value = rows
    return db


def _client(templates, workspaces) -> MagicMock:
    client = MagicMock()
    client.list_templates = AsyncMock(return_value=templates)
    client.list_all_workspaces = AsyncMock(return_value=workspaces)
    return client


@pytest.fixture
def templates_root(tmp_path):
    """Two templates on disk: 'vscode' and 'matlab'."""
    root = tmp_path / "templates"
    for dir_name, manifest in (
        ("vscode", {
            "coder_template_name": "vscode-workspace",
            "image_name": "computor-workspace-vscode",
            "display_name": "VS Code",
            "description": "VS Code in the browser",
            "icon": "/icon/code.svg",
        }),
        ("matlab", {
            "coder_template_name": "matlab-workspace",
            "image_name": "computor-workspace-matlab",
            "display_name": "MATLAB",
        }),
    ):
        tpl = root / dir_name
        tpl.mkdir(parents=True)
        (tpl / "template.json").write_text(json.dumps(manifest))
        (tpl / templates_fs.MANAGED_MARKER).write_text("")
    return str(root)


# --- catalog -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_catalog_lists_undeployed_templates(templates_root):
    """The whole point: a template on disk that Coder does not have is listed."""
    coder_templates = [CoderTemplate(
        id="t-vscode", name="vscode-workspace", display_name="VS Code",
        active_version_id="v1",
    )]
    response = await list_template_catalog(
        _admin(), _settings(templates_root), _client(coder_templates, []), _db([]),
    )

    by_name = {entry.name: entry for entry in response.templates}
    assert set(by_name) == {"vscode-workspace", "matlab-workspace"}

    assert by_name["vscode-workspace"].deployed is True
    assert by_name["vscode-workspace"].template_id == "t-vscode"

    matlab = by_name["matlab-workspace"]
    assert matlab.deployed is False
    assert matlab.dir_name == "matlab"          # so the UI can offer a Deploy
    assert matlab.active_version_id is None
    # Manifest metadata survives even with nothing in Coder to read it from.
    assert matlab.display_name == "MATLAB"


@pytest.mark.asyncio
async def test_catalog_on_a_fresh_deployment_lists_everything_undeployed(templates_root):
    """Coder is empty until someone picks, so this is the first-run view.

    Every candidate is present and every one is deployable — which is what the
    admin UI turns into its "choose what this deployment offers" step.
    """
    response = await list_template_catalog(
        _admin(), _settings(templates_root), _client([], []), _db([]),
    )
    assert len(response.templates) == 2
    assert all(not entry.deployed for entry in response.templates)
    assert all(entry.dir_name for entry in response.templates)


@pytest.mark.asyncio
async def test_catalog_keeps_a_template_coder_has_but_disk_does_not(templates_root):
    """A hand-pushed template still has workspaces on it — never drop it."""
    stray = CoderTemplate(id="t-stray", name="legacy-workspace", display_name="Legacy")
    response = await list_template_catalog(
        _admin(), _settings(templates_root), _client([stray], []), _db([]),
    )
    entry = next(e for e in response.templates if e.name == "legacy-workspace")
    assert entry.deployed is True
    # No directory means no image to rebuild — the UI hides Deploy on this.
    assert entry.dir_name is None


@pytest.mark.asyncio
async def test_catalog_counts_workspaces_and_seats(templates_root):
    """Seats count what the quota counts: a start build in an active state."""
    coder_templates = [CoderTemplate(id="t-vscode", name="vscode-workspace")]
    workspaces = [
        CoderWorkspace(
            id="w1", name="w1", owner_id="u1", template_id="t-vscode",
            latest_build_transition="start",
            latest_build_status=WorkspaceBuildStatus.RUNNING,
        ),
        CoderWorkspace(  # stopped: its last build succeeded, at stopping
            id="w2", name="w2", owner_id="u2", template_id="t-vscode",
            latest_build_transition="stop",
            latest_build_status=WorkspaceBuildStatus.SUCCEEDED,
        ),
    ]
    response = await list_template_catalog(
        _admin(), _settings(templates_root), _client(coder_templates, workspaces), _db([]),
    )
    entry = next(e for e in response.templates if e.name == "vscode-workspace")
    assert entry.workspace_count == 2
    assert entry.running_workspace_count == 1


@pytest.mark.asyncio
async def test_catalog_reports_enabled_from_the_settings_row(templates_root):
    """No row means enabled; a row saying otherwise wins."""
    rows = [WorkspaceTemplateSettings(template_name="matlab-workspace", enabled=False)]
    response = await list_template_catalog(
        _admin(), _settings(templates_root), _client([], []), _db(rows),
    )
    by_name = {entry.name: entry for entry in response.templates}
    assert by_name["matlab-workspace"].enabled is False
    assert by_name["vscode-workspace"].enabled is True


@pytest.mark.asyncio
async def test_catalog_survives_an_unreadable_templates_directory():
    """Without the mount there is nothing on disk — list Coder and say so."""
    coder_templates = [CoderTemplate(id="t-vscode", name="vscode-workspace")]
    response = await list_template_catalog(
        _admin(), _settings("/nonexistent"), _client(coder_templates, []), _db([]),
    )
    assert response.templates_dir_available is False
    assert [entry.name for entry in response.templates] == ["vscode-workspace"]
