"""Tests for ``view_mappers._build_repository`` after the provider-agnostic switch:
the new ``properties['git']`` block is preferred, the legacy ``'gitlab'`` block is
the fallback."""
from types import SimpleNamespace

from computor_backend.repositories.view_mappers import _build_repository


def _sg(properties):
    return SimpleNamespace(properties=properties)


def test_provider_agnostic_git_block():
    repo = _build_repository(_sg({"git": {
        "provider": "forgejo",
        "server_url": "http://localhost:3030",
        "repo_ref": "itpcp-matlab-2027/tphi",
        "http_url": "http://localhost:3030/itpcp-matlab-2027/tphi.git",
        "web_url": "http://localhost:3030/itpcp-matlab-2027/tphi",
    }}))
    assert repo.provider == "forgejo"
    assert repo.full_path == "itpcp-matlab-2027/tphi"
    assert repo.clone_url == "http://localhost:3030/itpcp-matlab-2027/tphi.git"
    assert repo.web_url.endswith("/tphi")


def test_git_clone_url_derived_when_missing():
    # No explicit http_url -> derive from server_url + repo_ref.
    repo = _build_repository(_sg({"git": {
        "provider": "forgejo",
        "server_url": "http://localhost:3030/",
        "repo_ref": "org/repo",
    }}))
    assert repo.clone_url == "http://localhost:3030/org/repo.git"


def test_legacy_gitlab_fallback():
    repo = _build_repository(_sg({"gitlab": {
        "url": "http://gitlab.example",
        "full_path": "grp/sub/mmusterm",
        "web_url": "http://gitlab.example/grp/sub/mmusterm",
    }}))
    assert repo.provider == "gitlab"
    assert repo.full_path == "grp/sub/mmusterm"
    assert repo.clone_url == "http://gitlab.example/grp/sub/mmusterm.git"


def test_git_preferred_over_gitlab():
    repo = _build_repository(_sg({
        "git": {"provider": "forgejo", "server_url": "http://f", "repo_ref": "o/r",
                "http_url": "http://f/o/r.git"},
        "gitlab": {"url": "http://g", "full_path": "x/y"},
    }))
    assert repo.provider == "forgejo" and repo.full_path == "o/r"


def test_none_when_no_properties():
    assert _build_repository(SimpleNamespace(properties=None)) is None
