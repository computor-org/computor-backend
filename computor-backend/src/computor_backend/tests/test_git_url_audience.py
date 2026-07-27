"""Git URLs are rendered for the audience asking for them.

A browser gets the public host. A Coder workspace gets the host it can actually
reach through workspace-ingress — it deliberately cannot resolve the public
domain, which is what keeps it off everything else the platform serves, and an
internet-disabled workspace could not reach it even if it could.
"""

import pytest

from computor_backend.git_server import config as git_config
from computor_backend.git_server.config import (
    WORKSPACE_CLIENT_VALUE,
    set_git_audience,
    to_public_git_url,
    to_workspace_git_url,
)


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    """Each test picks its own audience; the default must not leak between them."""
    monkeypatch.setenv("GIT_SERVER_URL", "http://computor-forgejo:3030")
    monkeypatch.setenv("GIT_SERVER_URL_PUBLIC", "https://public.example/forgejo")
    monkeypatch.setenv("FORGEJO_ROOT_URL", "https://public.example/forgejo")
    git_config.get_git_server_settings.cache_clear()
    set_git_audience("public")
    yield
    set_git_audience("public")
    git_config.get_git_server_settings.cache_clear()


STORED = "http://computor-forgejo:3030/course/repo.git"


def test_browser_gets_the_public_host():
    assert to_public_git_url(STORED) == "https://public.example/forgejo/course/repo.git"


def test_workspace_gets_the_reachable_host():
    set_git_audience(WORKSPACE_CLIENT_VALUE)
    assert to_public_git_url(STORED) == "http://computor-git/course/repo.git"


def test_a_public_url_is_also_rewritten_for_a_workspace():
    """Some URLs are already public by the time they reach the renderer; a
    workspace still cannot resolve that host, so they must be swapped too."""
    assert (
        to_workspace_git_url("https://public.example/forgejo/course/repo.git")
        == "http://computor-git/course/repo.git"
    )


def test_foreign_hosts_are_left_alone():
    """An external GitLab is not ours to rewrite, for either audience."""
    external = "https://gitlab.com/someone/repo.git"
    assert to_public_git_url(external) == external
    set_git_audience(WORKSPACE_CLIENT_VALUE)
    assert to_public_git_url(external) == external


def test_empty_urls_survive():
    for value in (None, ""):
        assert to_public_git_url(value) == value
        assert to_workspace_git_url(value) == value
