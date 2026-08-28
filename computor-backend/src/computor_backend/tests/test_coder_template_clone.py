"""Template lifecycle endpoints: create (clone) and delete.

A clone is a directory the repo sync never sees, so the endpoints' job is to
keep its identity unique — on disk AND in Coder — and to refuse deletion while
anything still depends on it.
"""

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from computor_backend.api.coder import (
    create_template,
    delete_template,
    list_template_catalog,
)
from computor_backend.coder import templates_fs
from computor_backend.coder.config import CoderSettings
from computor_backend.coder.exceptions import CoderConnectionError
from computor_backend.coder.schemas import (
    CoderTemplate,
    CoderWorkspace,
    TemplateCloneRequest,
    WorkspaceBuildStatus,
)
from computor_backend.exceptions import (
    BadRequestException,
    ConflictException,
    ServiceUnavailableException,
)
from computor_backend.model.workspace import WorkspaceTemplateSettings
from computor_backend.permissions.principal import Principal


@pytest.fixture(autouse=True)
def no_deployment_fallback(monkeypatch):
    """Templates resolve from the fixture root only (see test_coder_template_catalog)."""
    monkeypatch.delenv("SYSTEM_DEPLOYMENT_PATH", raising=False)


@pytest.fixture(autouse=True)
def no_running_coder_task():
    with patch(
        "computor_backend.api.coder._reject_conflicting_coder_task", AsyncMock(),
    ) as guard:
        yield guard


def _admin() -> Principal:
    return Principal(user_id="admin", roles=["_admin"])


def _settings(templates_dir: str) -> CoderSettings:
    return CoderSettings(
        admin_email="admin@example.com",
        admin_password="x",
        templates_dir=templates_dir,
    )


def _client(templates=(), workspaces=()) -> MagicMock:
    client = MagicMock()
    client.list_templates = AsyncMock(return_value=list(templates))
    client.list_all_workspaces = AsyncMock(return_value=list(workspaces))
    client.delete_template = AsyncMock()
    client.patch_template_meta = AsyncMock()
    return client


def _db(settings_row=None) -> MagicMock:
    db = MagicMock()
    db.query.return_value.all.return_value = [settings_row] if settings_row else []
    db.query.return_value.filter.return_value.first.return_value = settings_row
    db.query.return_value.filter.return_value.delete.return_value = 1 if settings_row else 0
    return db


VSCODE_MANIFEST = {
    "coder_template_name": "vscode-workspace",
    "image_name": "computor-workspace-vscode",
    "source_repos": [{"url": "https://x/y.git", "ref": "main", "sha_build_arg": "SHA"}],
    "display_name": "VS Code",
    "description": "VS Code in the browser",
    "icon": "/icon/code.svg",
}


@pytest.fixture
def templates_root(tmp_path):
    """One managed 'vscode' template with a Dockerfile and a payload dir."""
    root = tmp_path / "templates"
    tpl = root / "vscode"
    (tpl / "figures").mkdir(parents=True)
    (tpl / "template.json").write_text(json.dumps(VSCODE_MANIFEST))
    (tpl / "Dockerfile").write_text("FROM scratch\n")
    (tpl / "main.tf").write_text("")
    (tpl / "figures" / "x.py").write_text("")
    (tpl / templates_fs.MANAGED_MARKER).write_text("")
    return str(root)


def _request(**overrides) -> TemplateCloneRequest:
    body = {
        "source": "vscode-workspace",
        "key": "py-ds",
        "display_name": "Python DS",
        "description": "Data science",
        "icon": "https://x/py.svg",
    }
    body.update(overrides)
    return TemplateCloneRequest(**body)


def _clone_on_disk(root: str) -> str:
    templates_fs.clone_template(
        root, "vscode", "py-ds", display_name="Python DS", description=None, icon=None,
    )
    return os.path.join(root, "py-ds")


# --- create ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_then_catalog_lists_the_clone(templates_root):
    """The whole point: a new, independent, undeployed template shows up
    next to the shipped ones — and the shipped one is untouched."""
    client = _client()
    created = await create_template(
        _request(), _admin(), _settings(templates_root), client, _db(),
    )
    assert created.template_name == "py-ds-workspace"
    assert created.dir_name == "py-ds"
    assert created.image_name == "computor-workspace-py-ds"
    assert created.display_name == "Python DS"
    assert created.icon == "https://x/py.svg"
    assert created.cloned_from == "vscode"
    assert created.created_at is not None
    assert created.customized is True

    clone = os.path.join(templates_root, "py-ds")
    assert os.path.isfile(os.path.join(clone, "Dockerfile"))
    assert os.path.isfile(os.path.join(clone, "figures", "x.py"))
    assert not os.path.exists(os.path.join(clone, templates_fs.MANAGED_MARKER))
    assert not templates_fs.is_customized(os.path.join(templates_root, "vscode"))

    response = await list_template_catalog(
        _admin(), _settings(templates_root), client, _db(),
    )
    by_name = {entry.name: entry for entry in response.templates}
    entry = by_name["py-ds-workspace"]
    assert entry.dir_name == "py-ds"          # what the UI feeds into Deploy
    assert entry.cloned_from == "vscode"
    assert entry.deployed is False
    assert entry.customized is True
    assert entry.image_name == "computor-workspace-py-ds"
    assert by_name["vscode-workspace"].cloned_from is None


@pytest.mark.asyncio
async def test_create_refuses_a_name_coder_already_has(templates_root):
    """A live template with no directory here would be shown as the clone's
    deployment and pushed over by the worker — refuse before copying."""
    stray = CoderTemplate(id="t-stray", name="py-ds-workspace", display_name="Stray")
    with pytest.raises(ConflictException):
        await create_template(
            _request(), _admin(), _settings(templates_root), _client([stray]), _db(),
        )
    assert not os.path.exists(os.path.join(templates_root, "py-ds"))


@pytest.mark.asyncio
async def test_create_refuses_when_coder_is_unreachable(templates_root):
    """Uniqueness against live state cannot be checked — so nothing is created."""
    client = _client()
    client.list_templates = AsyncMock(side_effect=CoderConnectionError())
    with pytest.raises(ServiceUnavailableException):
        await create_template(_request(), _admin(), _settings(templates_root), client, _db())
    assert sorted(os.listdir(templates_root)) == ["vscode"]


@pytest.mark.asyncio
@pytest.mark.parametrize("key", ["Py_DS", "py-workspace", "-py"])
async def test_create_rejects_a_bad_key_with_400(templates_root, key):
    with pytest.raises(BadRequestException):
        await create_template(
            _request(key=key), _admin(), _settings(templates_root), _client(), _db(),
        )
    assert sorted(os.listdir(templates_root)) == ["vscode"]


@pytest.mark.asyncio
async def test_create_rejects_a_taken_key_with_409(templates_root):
    with pytest.raises(ConflictException):
        await create_template(
            _request(key="vscode"), _admin(), _settings(templates_root), _client(), _db(),
        )


@pytest.mark.asyncio
async def test_create_copies_the_source_settings_row(templates_root):
    """Limits, quota, policy and overrides travel with the copy."""
    source_row = WorkspaceTemplateSettings(
        template_name="vscode-workspace", enabled=False, memory_mb=2048, cpu_shares=0,
        max_running_workspaces=3, allow_root=True, allow_internet=False,
        template_variables={"code_server_port": "13337"},
    )
    db = _db(source_row)
    await create_template(_request(), _admin(), _settings(templates_root), _client(), db)
    db.add.assert_called_once()
    copied = db.add.call_args.args[0]
    assert isinstance(copied, WorkspaceTemplateSettings)
    assert copied.template_name == "py-ds-workspace"
    assert copied.enabled is False
    assert copied.memory_mb == 2048
    assert copied.max_running_workspaces == 3
    assert copied.allow_root is True
    assert copied.allow_internet is False
    assert copied.template_variables == {"code_server_port": "13337"}
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_without_a_source_row_adds_nothing(templates_root):
    db = _db()
    await create_template(_request(), _admin(), _settings(templates_root), _client(), db)
    db.add.assert_not_called()


# --- delete ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_refuses_a_repo_managed_template(templates_root):
    """computor.sh would only seed it again — and its Coder template is in use."""
    client = _client()
    with pytest.raises(BadRequestException):
        await delete_template(
            "vscode-workspace", _admin(), _settings(templates_root), client, _db(),
        )
    assert os.path.isfile(os.path.join(templates_root, "vscode", "template.json"))
    client.delete_template.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_refuses_a_clone_with_workspaces(templates_root):
    clone = _clone_on_disk(templates_root)
    live = CoderTemplate(id="t-py", name="py-ds-workspace")
    workspace = CoderWorkspace(
        id="w1", name="py-ds", owner_id="u1", template_id="t-py",
        latest_build_transition="stop", latest_build_status=WorkspaceBuildStatus.SUCCEEDED,
    )
    client = _client([live], [workspace])
    with pytest.raises(ConflictException):
        await delete_template(
            "py-ds-workspace", _admin(), _settings(templates_root), client, _db(),
        )
    assert os.path.isdir(clone)
    client.delete_template.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_removes_coder_disk_and_db_rows(templates_root):
    clone = _clone_on_disk(templates_root)
    live = CoderTemplate(id="t-py", name="py-ds-workspace")
    client = _client([live], [])
    db = _db(WorkspaceTemplateSettings(template_name="py-ds-workspace"))

    response = await delete_template(
        "py-ds-workspace", _admin(), _settings(templates_root), client, db,
    )

    client.delete_template.assert_awaited_once_with("t-py")
    assert not os.path.exists(clone)
    assert sorted(os.listdir(templates_root)) == ["vscode"]
    # Settings row and course assignments, both by the Coder name.
    assert db.query.return_value.filter.return_value.delete.call_count == 2
    db.commit.assert_called_once()
    assert response.success is True
    assert response.coder_deleted is True
    assert response.settings_deleted is True
    assert "computor-workspace-py-ds" in response.message


@pytest.mark.asyncio
async def test_delete_of_an_undeployed_clone_skips_coder(templates_root):
    clone = _clone_on_disk(templates_root)
    client = _client()
    response = await delete_template(
        "py-ds", _admin(), _settings(templates_root), client, _db(),
    )
    client.delete_template.assert_not_awaited()
    assert response.coder_deleted is False
    assert not os.path.exists(clone)


@pytest.mark.asyncio
async def test_delete_is_refused_while_a_coder_task_runs(templates_root, no_running_coder_task):
    """A running build/push may be reading the directory."""
    clone = _clone_on_disk(templates_root)
    no_running_coder_task.side_effect = ConflictException(detail="push running")
    with pytest.raises(ConflictException):
        await delete_template(
            "py-ds-workspace", _admin(), _settings(templates_root), _client(), _db(),
        )
    assert os.path.isdir(clone)
