"""Tests for pinning a workspace image to its source repo's current commit.

Docker keys a ``RUN`` layer on its command string, so a Dockerfile that checks
out a *branch name* produces an identical instruction on every build and keeps
the first checkout it ever made. The VS Code templates build the Computor
extension that way, so new extension commits never reached the images — and the
build reported success either way, which is how it went unnoticed. Resolving the
ref to a commit and passing it as a build arg moves the layer's cache key
exactly when the source moves.
"""

from unittest.mock import patch

from computor_backend.tasks.temporal_coder_setup import (
    _resolve_remote_sha,
    _source_repo_build_args,
)

SHA = "4f8cda4201a7424a4985e0ef44a37094d5a6aed9"
REPO = {
    "url": "https://example.invalid/computor-vscode.git",
    "ref": "release/2026.10",
    "sha_build_arg": "EXTENSION_REPO_SHA",
}


def test_resolved_commit_becomes_a_build_arg():
    with patch(
        "computor_backend.tasks.temporal_coder_setup._resolve_remote_sha",
        return_value=SHA,
    ):
        assert _source_repo_build_args({"source_repos": [REPO]}, "vscode") == {
            "EXTENSION_REPO_SHA": SHA
        }


def test_template_without_source_repos_is_untouched():
    """bash/jupyter/ubuntu-desktop clone nothing and must not pay for a lookup."""
    with patch(
        "computor_backend.tasks.temporal_coder_setup._resolve_remote_sha"
    ) as resolve:
        assert _source_repo_build_args({}, "bash") == {}
        resolve.assert_not_called()


def test_unresolvable_repo_is_skipped_not_fatal():
    """An unreachable forge must not block a rebuild that may not even involve it.

    The build then runs from cache, so this is deliberately logged loudly.
    """
    with patch(
        "computor_backend.tasks.temporal_coder_setup._resolve_remote_sha",
        return_value=None,
    ):
        assert _source_repo_build_args({"source_repos": [REPO]}, "vscode") == {}


def test_malformed_entry_is_skipped():
    entries = [{"url": "x"}, {"ref": "y"}, {**REPO, "sha_build_arg": None}]
    with patch(
        "computor_backend.tasks.temporal_coder_setup._resolve_remote_sha",
        return_value=SHA,
    ):
        assert _source_repo_build_args({"source_repos": entries}, "vscode") == {}


def test_resolve_remote_sha_parses_ls_remote_output():
    completed = type("P", (), {"returncode": 0, "stdout": f"{SHA}\trefs/heads/release/2026.10\n", "stderr": ""})
    with patch("subprocess.run", return_value=completed):
        assert _resolve_remote_sha("https://example.invalid/r.git", "release/2026.10") == SHA


def test_resolve_remote_sha_ignores_peeled_tag_line():
    """`ls-remote` lists an annotated tag twice; the ^{} peel is not the ref."""
    out = f"{SHA}\trefs/tags/v1\ndeadbeef00000000000000000000000000000000\trefs/tags/v1^{{}}\n"
    completed = type("P", (), {"returncode": 0, "stdout": out, "stderr": ""})
    with patch("subprocess.run", return_value=completed):
        assert _resolve_remote_sha("https://example.invalid/r.git", "v1") == SHA


def test_resolve_remote_sha_returns_none_on_failure():
    completed = type("P", (), {"returncode": 128, "stdout": "", "stderr": "not found"})
    with patch("subprocess.run", return_value=completed):
        assert _resolve_remote_sha("https://example.invalid/r.git", "nope") is None
