"""Template lifecycle on disk: clone, metadata, delete.

A clone is a real directory next to the shipped ones, so the properties that
matter are the ones computor.sh and the push worker rely on: it carries no
managed marker, its identity is unique across every template on disk, and a
half-copied dir is never visible to a discoverer.
"""

import json
import os
import shutil

import pytest

from computor_backend.coder import templates_fs


def _write_template(root, dir_name, manifest, *, managed=True, files=()):
    tpl = root / dir_name
    tpl.mkdir(parents=True)
    (tpl / "template.json").write_text(json.dumps(manifest))
    for rel, content in files:
        target = tpl / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    if managed:
        (tpl / templates_fs.MANAGED_MARKER).write_text("")
    return tpl


SOURCE_REPOS = [{"url": "https://x/y.git", "ref": "main", "sha_build_arg": "SHA"}]


@pytest.fixture
def root(tmp_path):
    """A managed 'vscode' template with a Dockerfile and a nested payload."""
    root = tmp_path / "templates"
    _write_template(root, "vscode", {
        "coder_template_name": "vscode-workspace",
        "image_name": "computor-workspace-vscode",
        "build_args_env": [],
        "source_repos": SOURCE_REPOS,
        "display_name": "VS Code",
        "description": "VS Code in the browser",
        "icon": "/icon/code.svg",
    }, files=(
        ("Dockerfile", "FROM scratch\n"),
        ("main.tf", ""),
        ("figures/computor_figures.py", "print('hi')\n"),
    ))
    return root


def _clone(root, key, **overrides):
    kwargs = {"display_name": "x", "description": None, "icon": None}
    kwargs.update(overrides)
    return templates_fs.clone_template(str(root), "vscode", key, **kwargs)


def test_clone_copies_tree_without_marker_and_rewrites_manifest(root):
    dir_name, manifest = _clone(
        root, "py-ds",
        display_name="Python DS", description="Data science", icon="https://x/py.svg",
    )
    clone = root / "py-ds"
    assert dir_name == "py-ds"
    assert (clone / "Dockerfile").read_text() == "FROM scratch\n"
    assert (clone / "figures" / "computor_figures.py").exists()
    # No marker: computor.sh never visits a dir without a repo counterpart,
    # and a marker would claim otherwise.
    assert not (clone / templates_fs.MANAGED_MARKER).exists()
    assert templates_fs.is_customized(str(clone))

    on_disk = json.loads((clone / "template.json").read_text())
    assert on_disk["coder_template_name"] == "py-ds-workspace"
    assert on_disk["image_name"] == "computor-workspace-py-ds"
    assert on_disk["display_name"] == "Python DS"
    assert on_disk["description"] == "Data science"
    assert on_disk["icon"] == "https://x/py.svg"
    assert on_disk["cloned_from"] == "vscode"
    assert on_disk["created_at"]
    assert on_disk["source_repos"] == SOURCE_REPOS  # inherited
    assert "dir_name" not in on_disk
    assert manifest["dir_name"] == "py-ds"
    assert templates_fs.is_clone(on_disk)

    # No staging leftovers; both identities resolve to the new dir.
    assert not [e for e in os.listdir(root) if e.startswith(".")]
    assert templates_fs.resolve_template_dir(str(root), "py-ds-workspace") == ("py-ds", str(clone))
    assert templates_fs.resolve_template_dir(str(root), "py-ds") == ("py-ds", str(clone))
    # The source is untouched, marker included.
    assert not templates_fs.is_customized(str(root / "vscode"))


def test_clone_rejects_names_taken_by_dir_coder_name_or_image(root):
    with pytest.raises(templates_fs.TemplateConflictError):
        _clone(root, "vscode")
    # A template whose CODER name is 'legacy-workspace' lives in dir 'old':
    # key 'legacy' would derive that same Coder name.
    _write_template(root, "old", {
        "coder_template_name": "legacy-workspace", "image_name": "computor-workspace-old",
    })
    with pytest.raises(templates_fs.TemplateConflictError):
        _clone(root, "legacy")
    # Image name taken by a manifest whose names differ.
    _write_template(root, "other", {
        "coder_template_name": "other-workspace", "image_name": "computor-workspace-ds",
    })
    with pytest.raises(templates_fs.TemplateConflictError):
        _clone(root, "ds")
    # A plain (non-template) dir of that name.
    (root / "scratch").mkdir()
    with pytest.raises(templates_fs.TemplateConflictError):
        _clone(root, "scratch")
    assert set(templates_fs.discover_templates(str(root))) == {"vscode", "old", "other"}


@pytest.mark.parametrize("key", ["Py-DS", "-py", "py-", "py_ds", "a" * 23, "", "py-workspace"])
def test_clone_validates_key(root, key):
    with pytest.raises(templates_fs.TemplateFileError):
        _clone(root, key)
    assert sorted(os.listdir(root)) == ["vscode"]


def test_clone_requires_display_name_and_valid_icon(root):
    with pytest.raises(templates_fs.TemplateFileError):
        _clone(root, "a", display_name="  ")
    for icon in ("javascript:alert(1)", "icon/code.svg", "data:image/svg+xml;base64,AAA"):
        with pytest.raises(templates_fs.TemplateFileError):
            _clone(root, "a", icon=icon)
    for icon in ("https://x/py.svg", "http://x/py.png", "/icon/jupyter.svg", "", None):
        templates_fs.validate_icon(icon)
    assert sorted(os.listdir(root)) == ["vscode"]


def test_clone_leaves_no_staging_dir_on_failure(root, monkeypatch):
    real_copytree = shutil.copytree

    def copy_then_fail(src, dst, *args, **kwargs):
        # copytree recurses through the module-level name, hence *args.
        real_copytree(src, dst, *args, **kwargs)  # staging dir now exists
        raise OSError("disk full")

    monkeypatch.setattr(templates_fs.shutil, "copytree", copy_then_fail)
    with pytest.raises(OSError):
        _clone(root, "py-ds")
    assert sorted(os.listdir(root)) == ["vscode"]


def test_discover_skips_dot_dirs(root):
    _write_template(root, ".clone-py-ds-abc", {"coder_template_name": "py-ds-workspace"})
    assert set(templates_fs.discover_templates(str(root))) == {"vscode"}
    assert templates_fs.resolve_template_dir(str(root), "py-ds-workspace") is None


def test_update_metadata_flips_managed_and_validates_icon(root):
    tpl = str(root / "vscode")
    with pytest.raises(templates_fs.TemplateFileError):
        templates_fs.update_template_metadata(
            tpl, display_name="VS", description=None, icon="javascript:x",
        )
    with pytest.raises(templates_fs.TemplateFileError):
        templates_fs.update_template_metadata(tpl, display_name=" ", description=None, icon=None)
    assert not templates_fs.is_customized(tpl)  # a rejected write changes nothing

    manifest = templates_fs.update_template_metadata(
        tpl, display_name=" VS Code 2 ", description=None, icon=None,
    )
    assert manifest["display_name"] == "VS Code 2"
    on_disk = json.loads((root / "vscode" / "template.json").read_text())
    assert on_disk["display_name"] == "VS Code 2"
    # Cleared values are stored as "" so the next push clears them in Coder.
    assert on_disk["description"] == ""
    assert on_disk["icon"] == ""
    assert on_disk["source_repos"] == SOURCE_REPOS  # everything else survives
    assert templates_fs.is_customized(tpl)
    assert not (root / "vscode" / "template.json.tmp").exists()


def test_delete_template_dir_refuses_non_clone_and_removes_clone(root):
    with pytest.raises(templates_fs.TemplateFileError):
        templates_fs.delete_template_dir(str(root), "vscode")
    assert (root / "vscode" / "template.json").exists()

    _clone(root, "py-ds")
    templates_fs.delete_template_dir(str(root), "py-ds")
    assert not (root / "py-ds").exists()
    assert set(templates_fs.discover_templates(str(root))) == {"vscode"}
