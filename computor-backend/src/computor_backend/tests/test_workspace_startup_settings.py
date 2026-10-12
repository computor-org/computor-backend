"""Execute the managed editor settings writers without starting code-server."""

import json
import os
import subprocess
from pathlib import Path

import pytest


def _templates_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "ops" / "coder" / "templates"
        if candidate.is_dir():
            return candidate
    raise AssertionError("could not locate ops/coder/templates")


@pytest.fixture(params=["vscode", "matlab-vscode"])
def write_settings(request, tmp_path):
    template = (_templates_dir() / request.param / "startup.sh.tftpl").read_text()
    start = template.index('SETTINGS_FILE="$USER_DATA_DIR/User/settings.json"')
    end_marker = (
        "# Start code-server in background"
        if request.param == "vscode"
        else "# code-server compares its session cookie"
    )
    script = template[start:template.index(end_marker, start)]
    settings_file = tmp_path / "User" / "settings.json"

    def run():
        return subprocess.run(
            ["bash", "-c", script],
            env={**os.environ, "USER_DATA_DIR": str(tmp_path), "MATLAB_ROOT": "/opt/matlab/test"},
            check=True,
            capture_output=True,
            text=True,
        )

    return settings_file, run


def test_new_editor_settings_hide_secondary_sidebar(write_settings):
    settings_file, run = write_settings
    run()
    assert json.loads(settings_file.read_text())["workbench.secondarySideBar.defaultVisibility"] == "hidden"


def test_existing_settings_receive_default_without_changing_user_preferences(write_settings):
    settings_file, run = write_settings
    settings_file.parent.mkdir()
    original = {"workbench.colorTheme": "Default Light Modern", "editor.fontSize": 19}
    settings_file.write_text(json.dumps(original))
    run()
    result = json.loads(settings_file.read_text())
    assert result["workbench.secondarySideBar.defaultVisibility"] == "hidden"
    assert all(result[key] == value for key, value in original.items())
    first_write = settings_file.read_bytes()
    run()
    assert settings_file.read_bytes() == first_write


@pytest.mark.parametrize("visibility", ["visible", "maximizedInWorkspace"])
def test_explicit_secondary_sidebar_preference_is_preserved(write_settings, visibility):
    settings_file, run = write_settings
    settings_file.parent.mkdir()
    settings_file.write_text(json.dumps({"workbench.secondarySideBar.defaultVisibility": visibility}))
    run()
    assert json.loads(settings_file.read_text())["workbench.secondarySideBar.defaultVisibility"] == visibility


def test_commented_user_settings_are_not_rewritten(write_settings):
    settings_file, run = write_settings
    settings_file.parent.mkdir()
    original = '{\n  // Personal settings\n  "editor.fontSize": 19,\n}\n'
    settings_file.write_text(original)
    result = run()
    assert settings_file.read_text() == original
    assert "its settings stay as they are" in result.stderr
