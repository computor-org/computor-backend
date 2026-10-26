"""Exercise offline seeding without depending on a language-pack schema."""

import json
from pathlib import Path
import subprocess
import sys

import pytest


def _script():
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "ops/coder/templates/vscode/seed-language-packs.py"
        if candidate.is_file():
            return candidate
    raise AssertionError("cannot locate language-pack seed helper")


def _run(source, target, *, check=True):
    return subprocess.run(
        [sys.executable, str(_script()), str(source), str(target)],
        check=check, capture_output=True, text=True,
    )


def test_fresh_user_data_receives_native_entries_without_interpreting_them(tmp_path):
    source = tmp_path / "native.json"
    # Synthetic opaque native output: the helper must not invent entry fields.
    native = {"de": {"opaque_native_registration": ["hash", "absolute-path"]}}
    source.write_text(json.dumps(native))
    target = tmp_path / "fresh"
    _run(source, target)
    assert json.loads((target / "languagepacks.json").read_text()) == native


def test_retained_editor_state_and_other_languages_survive_refresh(tmp_path):
    source = tmp_path / "native.json"
    native = {"de": {"opaque_native_registration": "new-image"}}
    source.write_text(json.dumps(native))
    target = tmp_path / "retained"
    (target / "User").mkdir(parents=True)
    preserved = {
        "User/settings.json": b'{"workbench.colorTheme":"Default Light Modern"}',
        "User/argv.json": b'{"locale":"en","other-argument":true}',
        "User/globalStorage.json": b'{"extension-state":"keep"}',
        "workspace.py": b"print('learner files survive')\n",
    }
    for name, content in preserved.items():
        (target / name).write_bytes(content)
    registry = target / "languagepacks.json"
    registry.write_text(json.dumps({"de": {"old": True}, "fr": {"other-native": "keep"}}))
    _run(source, target)
    assert json.loads(registry.read_text()) == {**native, "fr": {"other-native": "keep"}}
    assert all((target / name).read_bytes() == content for name, content in preserved.items())
    original_stat = registry.stat()
    _run(source, target)
    assert registry.stat().st_mtime_ns == original_stat.st_mtime_ns


@pytest.mark.parametrize("invalid", ["{}", "not json"])
def test_invalid_image_registration_leaves_existing_registry_intact(tmp_path, invalid):
    source = tmp_path / "native.json"
    source.write_text(invalid)
    target = tmp_path / "retained"
    target.mkdir()
    registry = target / "languagepacks.json"
    before = b'{"fr":{"keep":"native"}}'
    registry.write_bytes(before)
    assert _run(source, target, check=False).returncode != 0
    assert registry.read_bytes() == before


def test_adapter_uses_installed_uuid_and_native_manifest_paths(tmp_path):
    import hashlib
    extensions = tmp_path / "extensions"
    pack = extensions / "german"
    pack.mkdir(parents=True)
    translation = pack / "core.json"
    translation.write_text('{"contents":{}}')
    identifier = {"id": "ms-ceintl.vscode-language-pack-de", "uuid": "synthetic-installed-uuid"}
    record = {"identifier": identifier, "version": "1.2.3", "location": {"path": str(pack)}}
    (extensions / "extensions.json").write_text(json.dumps([record]))
    manifest = {"version": "1.2.3", "contributes": {"localizations": [
        {"languageId": "de", "localizedLanguageName": "Deutsch", "languageName": "German",
         "translations": [{"id": "vscode", "path": "core.json"}]}]}}
    (pack / "package.json").write_text(json.dumps(manifest))
    output = tmp_path / "image"
    command = [sys.executable, str(_script()), "--build", str(extensions), str(output)]
    subprocess.run(command, check=True)
    entry = json.loads((output / "languagepacks.json").read_text())["de"]
    assert entry == {"hash": hashlib.md5(b"synthetic-installed-uuid1.2.3", usedforsecurity=False).hexdigest(),
                     "extensions": [{"extensionIdentifier": identifier, "version": "1.2.3"}],
                     "translations": {"vscode": str(translation)}, "label": "Deutsch"}
    translation.unlink()
    assert subprocess.run(command, capture_output=True).returncode != 0
