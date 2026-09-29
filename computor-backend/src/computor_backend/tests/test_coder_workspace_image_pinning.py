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


@pytest.fixture
def template_dir(tmp_path, monkeypatch):
    d = tmp_path / "bash"
    d.mkdir()
    (d / "Dockerfile").write_text("FROM scratch\n")
    (d / "template.json").write_text(json.dumps({"image_name": "ws-bash"}))
    monkeypatch.setattr(tcs.activity, "heartbeat", lambda *a: None)
    return tmp_path


def test_repo_digest_is_taken_for_the_right_repo_only():
    digests = [f"other:5000/ws-bash@{OTHER}", f"reg:5000/ws-bash@{DIGEST}"]
    assert tcs._repo_digest_of(digests, "reg:5000/ws-bash") == DIGEST
    assert tcs._repo_digest_of(digests[:1], "reg:5000/ws-bash") is None


# --- Real Docker + registry: two concurrent builds of the same template -------
#
# Build A and build B race on the shared :latest. Each must pin the digest of
# the image IT built (checked by pulling that digest and reading a marker
# file), whatever order the tag/push steps interleave in.


def _docker_or_skip():
    docker = pytest.importorskip("docker")
    try:
        client = docker.from_env()
        client.ping()
    except Exception:  # noqa: BLE001
        pytest.skip("no Docker daemon")
    return client


REGISTRY_IMAGE = "registry:2.8.3@sha256:a3d8aaa63ed8681a604f1dea0aa03f100d5895b6a58ace528858a7b332415373"
BASE = "alpine:3.20@sha256:d9e853e87e55526f6b2917df91a2115c36dd7c696a35be12163d44e6e2a4b6bc"


@pytest.mark.integration
def test_concurrent_builds_each_pin_their_own_image(tmp_path, monkeypatch):
    import threading
    from types import SimpleNamespace

    client = _docker_or_skip()
    try:
        reg = client.containers.run(
            REGISTRY_IMAGE,
            detach=True,
            remove=True,
            ports={"5000/tcp": ("127.0.0.1", None)},
        )
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"cannot start registry: {e}")
    try:
        reg.reload()
        port = reg.attrs["NetworkSettings"]["Ports"]["5000/tcp"][0]["HostPort"]
        registry = f"127.0.0.1:{port}"
        monkeypatch.setattr(tcs.activity, "heartbeat", lambda *a: None)
        monkeypatch.setattr(
            tcs,
            "get_worker_settings",
            lambda: SimpleNamespace(
                coder_registry_host=None, docker_socket_path="/var/run/docker.sock"
            ),
        )
        # The race window: stall every build right after it finishes, so the
        # other build moves :latest before this one tags and pushes.
        barrier = threading.Barrier(2, timeout=120)
        import docker as docker_sdk

        orig_build = docker_sdk.api.client.APIClient.build

        def slow_build(self, *a, **kw):
            yield from orig_build(self, *a, **kw)
            barrier.wait()

        monkeypatch.setattr(docker_sdk.api.client.APIClient, "build", slow_build)

        dirs, results = {}, {}
        for name in ("A", "B"):
            root = tmp_path / name
            d = root / "bash"
            d.mkdir(parents=True)
            (d / "Dockerfile").write_text(f"FROM {BASE}\nRUN echo {name} > /marker\n")
            (d / "template.json").write_text(json.dumps({"image_name": "ws-race"}))
            dirs[name] = root

        def run(name):
            results[name] = tcs.build_workspace_image(
                "bash",
                str(dirs[name]),
                registry,
                f"v20260929-120000-{name.lower()}00000",
            )

        threads = [threading.Thread(target=run, args=(n,)) for n in dirs]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=300)

        for name, res in results.items():
            assert res["success"], res
            ref = f"{registry}/ws-race@{res['digest']}"
            client.images.pull(ref)
            out = client.containers.run(ref, ["cat", "/marker"], remove=True)
            assert out.decode().strip() == name, f"build {name} pinned {out!r}"
        assert results["A"]["digest"] != results["B"]["digest"]
    finally:
        reg.remove(force=True)
