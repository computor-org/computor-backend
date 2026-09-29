"""A template version must be pinned to an immutable workspace image digest.

Every tag — ``:latest`` and the versioned ``:vYYYYMMDD-...`` alike — can be
re-pushed, so ``workspace_image`` is always ``<registry>/<image>@sha256:...``:
the digest the registry reported for this run's push, or (template push
without a build) the registry's current digest for the selected tag.
"""

import json

import pytest

from computor_backend.tasks import temporal_coder_setup as tcs
from computor_backend.tasks.temporal_coder_setup import (
    _stale_version_tags,
    _workspace_image_ref,
)

DIGEST = "sha256:" + "ab" * 32
OTHER = "sha256:" + "cd" * 32


def _never(name, tag):
    raise AssertionError("no registry lookup expected")


def test_build_digest_is_pinned_and_no_tag_is_trusted():
    ref = _workspace_image_ref(
        "registry:5000", "ws-bash", "v20260929-120000", DIGEST, _never
    )
    assert ref == f"registry:5000/ws-bash@{DIGEST}"


@pytest.mark.parametrize("tag", ["latest", "v20260929-120000", "stable"])
def test_push_without_build_resolves_the_selected_tag(tag):
    seen = []

    def resolve(name, t):
        seen.append((name, t))
        return OTHER

    ref = _workspace_image_ref("registry:5000", "ws-bash", tag, None, resolve)
    assert ref == f"registry:5000/ws-bash@{OTHER}"
    assert seen == [("ws-bash", tag)]


def test_unresolvable_tag_is_an_error_not_a_moving_tag():
    def missing(name, tag):
        raise LookupError("manifest unknown")

    with pytest.raises(LookupError):
        _workspace_image_ref("registry:5000", "ws-bash", "latest", None, missing)


def test_non_digest_is_rejected():
    with pytest.raises(ValueError):
        _workspace_image_ref("r:5000", "ws-bash", "latest", None, lambda n, t: "latest")


def test_generated_tags_with_run_suffix_are_still_cleanup_candidates():
    tags = [
        "v20260101-000000",
        "v20260929-120000-a1b2c3",
        "v20260929-120000-ffffff",
        "v20260928-000000",
        "latest",
    ]
    kept = set(tags) - set(_stale_version_tags(tags)) - {"latest"}
    assert "v20260929-120000-a1b2c3" in kept and "v20260929-120000-ffffff" in kept


class _FakeImage:
    def tag(self, repo, tag):
        pass


class _FakeClient:
    """Docker SDK stand-in: build succeeds, push reports per-tag digests."""

    def __init__(self, digests, style="aux", registry=None):
        self._digests = digests
        self._style = style
        self._registry = registry or {}
        self.api = self
        self.images = self

    def get_registry_data(self, ref):
        if ref not in self._registry:
            raise LookupError(ref)
        return type("RD", (), {"id": self._registry[ref]})()

    def build(self, **kw):
        yield {"stream": "Step 1/1"}

    def get(self, ref):
        return _FakeImage()

    def push(self, repo, tag, stream, decode):
        yield {"status": "Pushing"}
        if self._digests.get(tag):
            if self._style == "aux":
                yield {"aux": {"Tag": tag, "Digest": self._digests[tag], "Size": 1}}
            else:  # containerd image store: digest only in the status line
                yield {"status": f"{tag}: digest: {self._digests[tag]} size: 855"}


@pytest.fixture
def template_dir(tmp_path, monkeypatch):
    d = tmp_path / "bash"
    d.mkdir()
    (d / "Dockerfile").write_text("FROM scratch\n")
    (d / "template.json").write_text(json.dumps({"image_name": "ws-bash"}))
    monkeypatch.setattr(tcs.activity, "heartbeat", lambda *a: None)
    return tmp_path


def _build(monkeypatch, template_dir, digests, **client_kw):
    import docker

    monkeypatch.setattr(
        docker, "DockerClient", lambda **kw: _FakeClient(digests, **client_kw)
    )
    return tcs.build_workspace_image(
        "bash", str(template_dir), "reg:5000", "v20260929-120000-a1b2c3"
    )


@pytest.mark.parametrize("style", ["aux", "status"])
def test_build_returns_the_digest_of_the_versioned_push(
    monkeypatch, template_dir, style
):
    res = _build(
        monkeypatch,
        template_dir,
        {"latest": OTHER, "v20260929-120000-a1b2c3": DIGEST},
        style=style,
    )
    assert res["success"] is True
    assert res["digest"] == DIGEST
    assert res["image_ref"] == f"reg:5000/ws-bash@{DIGEST}"


def test_unreported_digest_falls_back_to_the_registry(monkeypatch, template_dir):
    res = _build(
        monkeypatch,
        template_dir,
        {"latest": OTHER},
        registry={"reg:5000/ws-bash:v20260929-120000-a1b2c3": DIGEST},
    )
    assert res["digest"] == DIGEST


def test_build_without_any_digest_fails(monkeypatch, template_dir):
    res = _build(monkeypatch, template_dir, {"latest": OTHER})
    assert res["success"] is False
