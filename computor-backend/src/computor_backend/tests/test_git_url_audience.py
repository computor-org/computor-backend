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


class TestPublicUrlPrecedence:
    """Which setting decides the host a student is handed.

    Production shipped clone URLs pointing at ``http://localhost:3030`` because
    a dev-scoped ``GIT_SERVER_URL`` reached ``GIT_SERVER_URL_PUBLIC`` through
    the prod compose file, where it shadowed the ``FORGEJO_ROOT_URL`` fallback.
    These pin the precedence the compose file now depends on.
    """

    def test_forgejo_root_url_is_used_when_no_explicit_public_url(self, monkeypatch):
        monkeypatch.delenv("GIT_SERVER_URL_PUBLIC", raising=False)
        monkeypatch.setenv("FORGEJO_ROOT_URL", "https://computor.at/forgejo")
        git_config.get_git_server_settings.cache_clear()
        assert (
            to_public_git_url(STORED) == "https://computor.at/forgejo/course/repo.git"
        )

    def test_empty_public_url_does_not_defeat_the_fallback(self, monkeypatch):
        """An unset variable arrives from compose as "", not as absent."""
        monkeypatch.setenv("GIT_SERVER_URL_PUBLIC", "")
        monkeypatch.setenv("FORGEJO_ROOT_URL", "https://computor.at/forgejo")
        git_config.get_git_server_settings.cache_clear()
        assert (
            to_public_git_url(STORED) == "https://computor.at/forgejo/course/repo.git"
        )

    def test_explicit_public_url_still_wins(self, monkeypatch):
        monkeypatch.setenv("GIT_SERVER_URL_PUBLIC", "https://git.example.org")
        monkeypatch.setenv("FORGEJO_ROOT_URL", "https://computor.at/forgejo")
        git_config.get_git_server_settings.cache_clear()
        assert to_public_git_url(STORED) == "https://git.example.org/course/repo.git"

    def test_the_shipped_regression_a_dev_host_reaching_students(self, monkeypatch):
        """The exact production state on 2026-09-03, before the fix.

        This asserts the broken behaviour is *reachable* when the dev value is
        allowed into the public slot, which is why the prod compose file no
        longer maps GIT_SERVER_URL there.
        """
        monkeypatch.setenv("GIT_SERVER_URL_PUBLIC", "http://localhost:3030")
        monkeypatch.setenv("FORGEJO_ROOT_URL", "https://computor.at/forgejo")
        git_config.get_git_server_settings.cache_clear()
        assert to_public_git_url(STORED) == "http://localhost:3030/course/repo.git"
