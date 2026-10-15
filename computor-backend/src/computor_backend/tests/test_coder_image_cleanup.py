"""Tests for the workspace-image cleanup activity (image pollution fix).

Every build+push run mints a fresh ``vYYYYMMDD-HHMMSS`` tag, so the build
host's docker daemon and the local registry accumulated one image generation
per rebuild (multi-GB for the MATLAB templates). The cleanup activity keeps
``:latest`` plus the IMAGE_VERSIONS_TO_KEEP newest versioned tags per repo and
removes the rest — locally by untagging, in the registry by asking the host's
computor-coder-hostops units for tag-dir removal + garbage collection.
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


def _settings():
    settings = MagicMock()
    settings.coder_registry_host = None
    settings.docker_host = None
    settings.docker_socket_path = "/var/run/docker.sock"
    return settings


def _run_cleanup(tmp_path, client, answer):
    """Run the activity with a faked docker client and host answer; return
    (result, the request the host was sent)."""
    docker_mod = MagicMock()
    docker_mod.DockerClient.return_value = client
    sent = {}

    def submit(action, fields, timeout, heartbeat=None):
        sent["action"], sent["fields"] = action, fields
        return answer

    with patch.dict(sys.modules, {"docker": docker_mod}), patch(
        "computor_backend.tasks.temporal_coder_setup.get_worker_settings",
        return_value=_settings(),
    ), patch(
        "computor_backend.tasks.temporal_coder_setup.coder_hostops.submit", submit
    ):
        result = cleanup_stale_workspace_images(
            ["vscode"], str(tmp_path), "localhost:5000"
        )
    return result, sent


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
    stale = ["v20260713-092229", "v20260710-185325"]
    answer = {
        "status": "ok",
        "removed": [f"computor-workspace-vscode:{t}" for t in stale]
        + ["someone-else:v20260101-000000"],
        "gc": "exit=0: blob eligible for deletion",
    }
    result, sent = _run_cleanup(tmp_path, client, answer)

    assert result["success"] is True
    # The two oldest versioned tags go; :latest and the newest two survive.
    assert result["removed_local"] == {"computor-workspace-vscode": stale}
    # Only repos this run asked about are reported back.
    assert result["removed_registry"] == {"computor-workspace-vscode": stale}
    assert result["gc"] == "exit=0: blob eligible for deletion"
    removed = [c.kwargs["image"] for c in client.images.remove.call_args_list]
    assert removed == [f"{repo}:{t}" for t in stale]
    # The registry part is the host's job now: no exec, no container lookup.
    client.containers.get.assert_not_called()
    assert sent["action"] == "registry-gc"
    assert sent["fields"] == [
        ("keep", str(IMAGE_VERSIONS_TO_KEEP)), ("repo", "computor-workspace-vscode"),
    ]


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
    answer = {"status": "error", "message": "host operations are not set up"}
    result, _ = _run_cleanup(tmp_path, client, answer)

    assert result["removed_local"] == {}
    assert len(result["skipped_in_use"]) == 1
    # A host that does not answer is reported, not raised.
    assert result["success"] is False
    assert any("not set up" in e for e in result["errors"])
    assert IMAGE_VERSIONS_TO_KEEP == 2  # retention contract the tests encode
