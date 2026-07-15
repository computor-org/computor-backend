"""Tests for the workspace-image cleanup activity (image pollution fix).

Every build+push run mints a fresh ``vYYYYMMDD-HHMMSS`` tag, so the build
host's docker daemon and the local registry accumulated one image generation
per rebuild (multi-GB for the MATLAB templates). The cleanup activity keeps
``:latest`` plus the IMAGE_VERSIONS_TO_KEEP newest versioned tags per repo and
removes the rest — locally by untagging, in the registry via exec'd tag-dir
removal + garbage collection.
"""

import json
import sys
from unittest.mock import MagicMock, patch

from computor_backend.tasks.temporal_coder_setup import (
    IMAGE_VERSIONS_TO_KEEP,
    _stale_version_tags,
    cleanup_stale_workspace_images,
)


def test_stale_version_tags_keeps_newest_versions_only():
    tags = [
        "latest",
        "v20260710-185325",
        "v20260713-092229",
        "v20260714-223158",
        "v20260714-225625",
    ]
    assert _stale_version_tags(tags) == ["v20260713-092229", "v20260710-185325"]


def test_stale_version_tags_never_touches_latest_or_custom_tags():
    # :latest, admin-chosen tags and malformed names are not candidates even
    # when more than IMAGE_VERSIONS_TO_KEEP tags exist.
    tags = ["latest", "stable", "v1.2.3", "rollback-target", "v20260714-225625"]
    assert _stale_version_tags(tags) == []


def test_stale_version_tags_under_retention_limit():
    assert _stale_version_tags(["latest", "v20260714-225625"]) == []
    assert _stale_version_tags([]) == []


def _image(tags):
    img = MagicMock()
    img.tags = tags
    return img


def _write_manifest(tmp_path, key, image_name):
    d = tmp_path / key
    d.mkdir()
    (d / "template.json").write_text(
        json.dumps({"coder_template_name": key, "image_name": image_name})
    )


def test_cleanup_prunes_local_and_registry(tmp_path):
    _write_manifest(tmp_path, "vscode", "computor-workspace-vscode")
    repo = "localhost:5000/computor-workspace-vscode"

    client = MagicMock()
    client.images.list.return_value = [
        _image([f"{repo}:latest", f"{repo}:v20260714-225625"]),
        _image([f"{repo}:v20260714-223158"]),
        _image([f"{repo}:v20260713-092229"]),
        _image([f"{repo}:v20260710-185325"]),
    ]
    registry = MagicMock()
    tags_dir = (
        "/var/lib/registry/docker/registry/v2/repositories/"
        "computor-workspace-vscode/_manifests/tags"
    )
    registry.exec_run.side_effect = [
        (0, b"latest\nv20260710-185325\nv20260713-092229\n"
            b"v20260714-223158\nv20260714-225625\n"),  # ls
        (0, b""),                                       # rm -rf
        (0, b"blob eligible for deletion\n"),           # garbage-collect
    ]
    client.containers.get.return_value = registry

    docker_mod = MagicMock()
    docker_mod.DockerClient.return_value = client
    settings = MagicMock()
    settings.coder_registry_host = None
    settings.docker_socket_path = "/var/run/docker.sock"
    settings.coder_registry_container = "computor-coder-registry"

    with patch.dict(sys.modules, {"docker": docker_mod}), patch(
        "computor_backend.tasks.temporal_coder_setup.get_worker_settings",
        return_value=settings,
    ):
        result = cleanup_stale_workspace_images(
            ["vscode"], str(tmp_path), "localhost:5000"
        )

    assert result["success"] is True
    # The two oldest versioned tags go; :latest and the newest two survive.
    stale = ["v20260713-092229", "v20260710-185325"]
    assert result["removed_local"] == {"computor-workspace-vscode": stale}
    assert result["removed_registry"] == {"computor-workspace-vscode": stale}
    removed = [c.kwargs["image"] for c in client.images.remove.call_args_list]
    assert removed == [f"{repo}:{t}" for t in stale]

    rm_call = registry.exec_run.call_args_list[1].args[0]
    assert rm_call[:2] == ["rm", "-rf"]
    assert set(rm_call[2:]) == {f"{tags_dir}/{t}" for t in stale}
    gc_call = registry.exec_run.call_args_list[2].args[0]
    assert gc_call[:2] == ["registry", "garbage-collect"]


def test_cleanup_keeps_in_use_images_and_never_raises(tmp_path):
    # An image whose last tag is held by a container makes docker 409 on
    # remove — the activity must record the skip and keep going.
    _write_manifest(tmp_path, "vscode", "computor-workspace-vscode")
    repo = "localhost:5000/computor-workspace-vscode"

    client = MagicMock()
    client.images.list.return_value = [
        _image([f"{repo}:latest", f"{repo}:v20260714-225625"]),
        _image([f"{repo}:v20260714-223158"]),
        _image([f"{repo}:v20260710-185325"]),
    ]
    client.images.remove.side_effect = Exception("409 image is in use")
    client.containers.get.side_effect = Exception("no such container")

    docker_mod = MagicMock()
    docker_mod.DockerClient.return_value = client
    settings = MagicMock()
    settings.coder_registry_host = None
    settings.docker_socket_path = "/var/run/docker.sock"
    settings.coder_registry_container = "computor-coder-registry"

    with patch.dict(sys.modules, {"docker": docker_mod}), patch(
        "computor_backend.tasks.temporal_coder_setup.get_worker_settings",
        return_value=settings,
    ):
        result = cleanup_stale_workspace_images(
            ["vscode"], str(tmp_path), "localhost:5000"
        )

    assert result["removed_local"] == {}
    assert len(result["skipped_in_use"]) == 1
    # Registry container unavailable is reported, not raised.
    assert result["success"] is False
    assert any("unavailable" in e for e in result["errors"])
    assert IMAGE_VERSIONS_TO_KEEP == 2  # retention contract the tests encode
