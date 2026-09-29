"""A template version must be pinned to an immutable workspace image.

``:latest`` moves with every build, so a template version pushed without a
build and pinned to it would silently change image under running workspaces.
Such a push resolves ``latest`` to the registry's current digest instead.
"""

import pytest

from computor_backend.tasks.temporal_coder_setup import _workspace_image_ref

DIGEST = "sha256:" + "ab" * 32


def test_versioned_tag_from_this_build_is_kept():
    def never(name):
        raise AssertionError("no lookup needed for a versioned tag")

    ref = _workspace_image_ref("registry:5000", "ws-bash", "v20260929-120000", never)
    assert ref == "registry:5000/ws-bash:v20260929-120000"


def test_latest_is_pinned_to_the_registry_digest():
    seen = []

    def resolve(name):
        seen.append(name)
        return DIGEST

    ref = _workspace_image_ref("registry:5000", "ws-bash", "latest", resolve)
    assert ref == f"registry:5000/ws-bash@{DIGEST}"
    assert seen == ["ws-bash"]


def test_unresolvable_latest_is_an_error_not_a_moving_tag():
    def missing(name):
        raise LookupError("manifest unknown")

    with pytest.raises(LookupError):
        _workspace_image_ref("registry:5000", "ws-bash", "latest", missing)
