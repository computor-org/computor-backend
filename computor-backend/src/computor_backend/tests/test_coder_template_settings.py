"""Per-template settings: push variable overrides, seat quota, template files."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from computor_backend.api.coder import (
    _enforce_template_quota,
    _per_template_variables,
    update_template_settings,
)
from computor_backend.coder import templates_fs
from computor_backend.coder.schemas import CoderWorkspace, WorkspaceBuildStatus
from computor_backend.exceptions import BadRequestException, ConflictException
from computor_backend.model.workspace import WorkspaceTemplateSettings
from computor_backend.permissions.principal import Principal
from computor_types.coder import WorkspaceTemplateSettingsUpdate


def _admin() -> Principal:
    return Principal(user_id="admin", roles=["_admin"])


def _db_returning(rows):
    """Mock Session whose query(...).all() / .filter(...).first() serve rows."""
    db = MagicMock()
    db.query.return_value.all.return_value = rows
    db.query.return_value.order_by.return_value.all.return_value = rows
    db.query.return_value.filter.return_value.first.return_value = (
        rows[0] if rows else None
    )
    return db


def _workspace(id_: str, template: str, transition="start",
               status=WorkspaceBuildStatus.SUCCEEDED) -> CoderWorkspace:
    return CoderWorkspace(
        id=id_, name=id_, owner_id="u1", template_id="t1",
        template_name=template, latest_build_transition=transition,
        latest_build_status=status,
    )


# --- push variable overrides -------------------------------------------------


def test_per_template_variables_stringifies_and_skips_unset_limits():
    rows = [
        WorkspaceTemplateSettings(
            template_name="matlab-ui-workspace", memory_mb=8192, cpu_shares=None,
            max_running_workspaces=5, template_variables={"shm_size": "1024"},
        ),
        WorkspaceTemplateSettings(  # quota only — nothing to push
            template_name="bash-workspace", memory_mb=None, cpu_shares=0,
            max_running_workspaces=3, template_variables={},
        ),
    ]
    overrides = _per_template_variables(_db_returning(rows))
    assert overrides == {
        "matlab-ui-workspace": {"memory_mb": "8192", "shm_size": "1024"},
    }


# --- seat quota --------------------------------------------------------------


@pytest.mark.asyncio
async def test_quota_blocks_when_running_seats_are_taken():
    row = WorkspaceTemplateSettings(
        template_name="matlab-ui-workspace", max_running_workspaces=2,
    )
    client = MagicMock()
    client.list_all_workspaces = AsyncMock(return_value=[
        _workspace("a", "matlab-ui-workspace"),
        _workspace("b", "matlab-ui-workspace", status=WorkspaceBuildStatus.STARTING),
        _workspace("stopped", "matlab-ui-workspace", transition="stop",
                   status=WorkspaceBuildStatus.STOPPED),
        _workspace("other", "vscode-workspace"),
    ])
    with pytest.raises(ConflictException):
        await _enforce_template_quota(_db_returning([row]), client, "matlab-ui-workspace")


@pytest.mark.asyncio
async def test_quota_excludes_the_target_workspace_and_ignores_unlimited():
    row = WorkspaceTemplateSettings(
        template_name="matlab-ui-workspace", max_running_workspaces=2,
    )
    client = MagicMock()
    client.list_all_workspaces = AsyncMock(return_value=[
        _workspace("a", "matlab-ui-workspace"),
        _workspace("b", "matlab-ui-workspace"),
    ])
    # Re-provisioning/starting workspace "b" itself does not count against it.
    await _enforce_template_quota(
        _db_returning([row]), client, "matlab-ui-workspace", exclude_workspace_id="b",
    )

    # No settings row → unlimited → Coder is never queried.
    await _enforce_template_quota(_db_returning([]), client, "vscode-workspace")


# --- settings endpoint validation --------------------------------------------


@pytest.mark.asyncio
async def test_settings_update_rejects_locked_variable_overrides():
    for variables in (
        {"workspace_image": "x"},   # push-managed
        {"docker_network": "x"},    # infrastructure wiring
    ):
        with pytest.raises(BadRequestException):
            await update_template_settings(
                "vscode-workspace",
                WorkspaceTemplateSettingsUpdate(template_variables=variables),
                _admin(), MagicMock(), _db_returning([]),
            )
    with pytest.raises(BadRequestException):
        await update_template_settings(
            "vscode-workspace",
            WorkspaceTemplateSettingsUpdate(cpu_shares=1),
            _admin(), MagicMock(), _db_returning([]),
        )


@pytest.mark.asyncio
async def test_settings_update_upserts_a_new_row():
    db = _db_returning([])
    result = await update_template_settings(
        "vscode-workspace",
        WorkspaceTemplateSettingsUpdate(
            memory_mb=2048, max_running_workspaces=10,
            template_variables={"code_server_port": "13337"},
        ),
        _admin(), MagicMock(), db,
    )
    db.add.assert_called_once()
    db.commit.assert_called_once()
    assert result.template_name == "vscode-workspace"
    assert result.memory_mb == 2048
    assert result.template_variables == {"code_server_port": "13337"}


# --- template files (templates_fs) -------------------------------------------


VARIABLES_TF = '''variable "app_port" {
  default     = 8080
  description = "App port"
  type        = number
}

variable "greeting" {
  default     = "hello"
  type        = string
}

variable "secret" {
  default     = "s3cret"
  type        = string
  sensitive   = true
}
'''


@pytest.fixture
def template_dir(tmp_path):
    root = tmp_path / "templates"
    tpl = root / "demo"
    tpl.mkdir(parents=True)
    (tpl / "template.json").write_text(json.dumps({"coder_template_name": "demo-workspace"}))
    (tpl / "variables.tf").write_text(VARIABLES_TF)
    (tpl / "main.tf").write_text("")
    (tpl / templates_fs.MANAGED_MARKER).write_text("")
    return str(root), str(tpl)


def test_resolve_and_parse_variables(template_dir):
    root, tpl = template_dir
    assert templates_fs.resolve_template_dir(root, "demo-workspace") == ("demo", tpl)
    assert templates_fs.resolve_template_dir(root, "demo") == ("demo", tpl)
    assert templates_fs.resolve_template_dir(root, "nope") is None

    parsed = {v["name"]: v for v in templates_fs.parse_template_variables(tpl)}
    assert parsed["app_port"]["default"] == 8080
    assert parsed["greeting"]["default"] == "hello"
    assert parsed["secret"]["sensitive"] is True
    assert parsed["secret"]["default"] is None  # masked


def test_write_template_file_gates_syntax_and_names(template_dir):
    _root, tpl = template_dir
    with pytest.raises(templates_fs.TemplateFileError):
        templates_fs.write_template_file(tpl, "variables.tf", 'variable "x" {')
    with pytest.raises(templates_fs.TemplateFileError):
        templates_fs.write_template_file(tpl, "../evil.tf", "")
    with pytest.raises(templates_fs.TemplateFileError):
        templates_fs.write_template_file(tpl, "new.tf", "")  # must already exist

    assert not templates_fs.is_customized(tpl)
    templates_fs.write_template_file(tpl, "main.tf", 'locals { a = 1 }\n')
    assert templates_fs.is_customized(tpl)

    templates_fs.restore_managed(tpl)
    assert not templates_fs.is_customized(tpl)
