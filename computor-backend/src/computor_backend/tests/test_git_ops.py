"""Functional tests for tasks.git_ops against local repositories."""
import os

import git
import pytest

from computor_backend.tasks.git_ops import (
    clone_or_init,
    commit_and_push,
    configure_identity,
)


@pytest.fixture
def bare_remote(tmp_path):
    remote = git.Repo.init(tmp_path / "origin.git", bare=True, initial_branch="main")
    return str(tmp_path / "origin.git")


def _write(repo_dir, name, content):
    with open(os.path.join(repo_dir, name), "w") as fh:
        fh.write(content)


def test_clone_or_init_falls_back_to_init(tmp_path):
    dest = str(tmp_path / "work")
    repo = clone_or_init("/nonexistent/nowhere.git", None, "gitlab", dest)
    assert repo.active_branch.name == "main"
    # non-http URL: no remote registered
    assert not repo.remotes


def test_commit_and_push_roundtrip(bare_remote, tmp_path):
    dest = str(tmp_path / "work")
    repo = clone_or_init(bare_remote, None, "gitlab", dest)
    if not repo.remotes:
        repo.create_remote("origin", bare_remote)
    configure_identity(repo)

    _write(dest, "a.txt", "hello")
    assert commit_and_push(repo, "first") is True

    clone_check = git.Repo.clone_from(bare_remote, str(tmp_path / "check"))
    assert (tmp_path / "check" / "a.txt").read_text() == "hello"


def test_commit_and_push_nothing_to_do(bare_remote, tmp_path):
    dest = str(tmp_path / "work")
    repo = clone_or_init(bare_remote, None, "gitlab", dest)
    if not repo.remotes:
        repo.create_remote("origin", bare_remote)
    configure_identity(repo)
    _write(dest, "a.txt", "hello")
    commit_and_push(repo, "first")

    # second call with no changes succeeds without a new commit
    head_before = repo.head.commit.hexsha
    assert commit_and_push(repo, "noop") is True
    assert repo.head.commit.hexsha == head_before


def test_push_retries_rebase_on_concurrent_push(bare_remote, tmp_path):
    # writer A
    a_dir = str(tmp_path / "a")
    repo_a = clone_or_init(bare_remote, None, "gitlab", a_dir)
    if not repo_a.remotes:
        repo_a.create_remote("origin", bare_remote)
    configure_identity(repo_a)
    _write(a_dir, "base.txt", "base")
    commit_and_push(repo_a, "base")

    # writer B clones, then A pushes again first (concurrent release)
    b_dir = str(tmp_path / "b")
    repo_b = git.Repo.clone_from(bare_remote, b_dir)
    configure_identity(repo_b)

    _write(a_dir, "a.txt", "from a")
    commit_and_push(repo_a, "from a")

    _write(b_dir, "b.txt", "from b")
    # B's push is non-fast-forward; rebase-retry must recover
    assert commit_and_push(repo_b, "from b") is True

    check = git.Repo.clone_from(bare_remote, str(tmp_path / "check"))
    assert (tmp_path / "check" / "a.txt").exists()
    assert (tmp_path / "check" / "b.txt").exists()


def test_no_remote_success_flag(tmp_path):
    dest = str(tmp_path / "work")
    repo = clone_or_init("/nonexistent/nowhere.git", None, "gitlab", dest)
    configure_identity(repo)
    _write(dest, "a.txt", "x")
    assert commit_and_push(repo, "msg") is True
    assert commit_and_push(repo, "msg2", success_without_remote=False) is True  # nothing to do
    _write(dest, "b.txt", "y")
    assert commit_and_push(repo, "msg3", success_without_remote=False) is False
