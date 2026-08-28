"""Template display metadata (display name / description / icon).

It lives in template.json — the same place the push pipeline reads it from —
so a save is a manifest write first and a live Coder patch second. The manifest
is the committed part; Coder being unavailable is reported, never fatal.
"""

import json
import os
from unittest.mock import AsyncMock, MagicMock

import pytest

from computor_backend.api.coder import (
    get_template_files,
    get_template_metadata,
    restore_template_managed,
    update_template_metadata,
)
from computor_backend.coder import templates_fs
from computor_backend.coder.config import CoderSettings
from computor_backend.coder.exceptions import CoderConnectionError
from computor_backend.coder.schemas import CoderTemplate, TemplateMetadataUpdate
from computor_backend.exceptions import BadRequestException
from computor_backend.permissions.principal import Principal


@pytest.fixture(autouse=True)
def no_deployment_fallback(monkeypatch):
    monkeypatch.delenv("SYSTEM_DEPLOYMENT_PATH", raising=False)


def _admin() -> Principal:
    return Principal(user_id="admin", roles=["_admin"])


def _settings(templates_dir: str) -> CoderSettings:
    return CoderSettings(
        admin_email="admin@example.com",
        admin_password="x",
        templates_dir=templates_dir,
    )


def _client(templates=()) -> MagicMock:
    client = MagicMock()
    client.list_templates = AsyncMock(return_value=list(templates))
    client.patch_template_meta = AsyncMock()
    return client


@pytest.fixture
def templates_root(tmp_path):
    root = tmp_path / "templates"
    tpl = root / "vscode"
    tpl.mkdir(parents=True)
    (tpl / "template.json").write_text(json.dumps({
        "coder_template_name": "vscode-workspace",
        "image_name": "computor-workspace-vscode",
        "display_name": "VS Code",
        "description": "VS Code in the browser",
        "icon": "/icon/code.svg",
    }))
    (tpl / "main.tf").write_text("")
    (tpl / templates_fs.MANAGED_MARKER).write_text("")
    return str(root)


def _manifest(root: str, dir_name: str) -> dict:
    with open(os.path.join(root, dir_name, "template.json")) as f:
        return json.load(f)


@pytest.mark.asyncio
async def test_update_writes_manifest_and_flips_customized(templates_root):
    response = await update_template_metadata(
        "vscode-workspace",
        TemplateMetadataUpdate(display_name="Code", description=None, icon=None),
        _admin(), _settings(templates_root), _client(),
    )
    on_disk = _manifest(templates_root, "vscode")
    assert on_disk["display_name"] == "Code"
    assert on_disk["description"] == ""   # cleared, not dropped: the push clears Coder too
    assert on_disk["icon"] == ""
    assert on_disk["image_name"] == "computor-workspace-vscode"
    assert response.display_name == "Code"
    assert response.customized is True
    assert templates_fs.is_customized(os.path.join(templates_root, "vscode"))
    # Not deployed: nothing to patch, and the response says when it applies.
    assert response.coder_updated is False
    assert "deployed" in response.message


@pytest.mark.asyncio
async def test_update_patches_the_live_coder_template(templates_root):
    settings = _settings(templates_root)
    client = _client([CoderTemplate(id="t-vscode", name="vscode-workspace")])
    response = await update_template_metadata(
        "vscode-workspace",
        TemplateMetadataUpdate(display_name="Code", description="Browser IDE", icon="https://x/c.svg"),
        _admin(), settings, client,
    )
    client.patch_template_meta.assert_awaited_once_with(
        "t-vscode",
        ttl_ms=settings.workspace_ttl_ms,
        activity_bump_ms=settings.workspace_activity_bump_ms,
        display_name="Code",
        description="Browser IDE",
        icon="https://x/c.svg",
    )
    assert response.coder_updated is True


@pytest.mark.asyncio
async def test_update_survives_a_coder_outage(templates_root):
    """The manifest is the source of truth; Coder catches up at the next push."""
    client = _client()
    client.list_templates = AsyncMock(side_effect=CoderConnectionError())
    response = await update_template_metadata(
        "vscode-workspace",
        TemplateMetadataUpdate(display_name="Code"),
        _admin(), _settings(templates_root), client,
    )
    assert _manifest(templates_root, "vscode")["display_name"] == "Code"
    assert response.coder_updated is False
    assert "next" in response.message


@pytest.mark.asyncio
async def test_update_rejects_a_bad_icon_and_changes_nothing(templates_root):
    with pytest.raises(BadRequestException):
        await update_template_metadata(
            "vscode-workspace",
            TemplateMetadataUpdate(display_name="Code", icon="javascript:alert(1)"),
            _admin(), _settings(templates_root), _client(),
        )
    assert _manifest(templates_root, "vscode")["display_name"] == "VS Code"
    assert not templates_fs.is_customized(os.path.join(templates_root, "vscode"))


@pytest.mark.asyncio
async def test_get_metadata_reads_the_manifest(templates_root):
    meta = await get_template_metadata("vscode", _admin(), _settings(templates_root))
    assert meta.template_name == "vscode-workspace"
    assert meta.dir_name == "vscode"
    assert meta.display_name == "VS Code"
    assert meta.icon == "/icon/code.svg"
    assert meta.image_name == "computor-workspace-vscode"
    assert meta.cloned_from is None
    assert meta.created_at is None
    assert meta.customized is False


@pytest.mark.asyncio
async def test_restore_managed_refuses_a_clone(templates_root):
    """A marker on a clone would only lie: computor.sh never visits it."""
    templates_fs.clone_template(
        templates_root, "vscode", "py-ds", display_name="Py", description=None, icon=None,
    )
    with pytest.raises(BadRequestException):
        await restore_template_managed("py-ds-workspace", _admin(), _settings(templates_root))
    assert not os.path.exists(os.path.join(templates_root, "py-ds", templates_fs.MANAGED_MARKER))

    # A customized repo template still can be restored.
    templates_fs.mark_customized(os.path.join(templates_root, "vscode"))
    response = await restore_template_managed("vscode-workspace", _admin(), _settings(templates_root))
    assert response.customized is False


@pytest.mark.asyncio
async def test_files_and_metadata_carry_cloned_from(templates_root):
    templates_fs.clone_template(
        templates_root, "vscode", "py-ds", display_name="Py", description=None, icon=None,
    )
    files = await get_template_files("py-ds-workspace", _admin(), _settings(templates_root))
    assert files.cloned_from == "vscode"
    assert files.customized is True
    meta = await get_template_metadata("py-ds-workspace", _admin(), _settings(templates_root))
    assert meta.cloned_from == "vscode"
    assert meta.created_at is not None
    vscode = await get_template_files("vscode-workspace", _admin(), _settings(templates_root))
    assert vscode.cloned_from is None
