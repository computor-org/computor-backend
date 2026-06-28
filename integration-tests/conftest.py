"""Integration-test fixtures for managed-GitLab course provisioning.

These run against a REAL GitLab (e.g. the local one on :8086). Configure via env:

    GITLAB_IT_URL=http://localhost:8086
    GITLAB_IT_TOKEN=<admin/group PAT>
    GITLAB_IT_PARENT_GROUP_ID=<numeric group id>

or drop them in ``integration-tests/.env.gitlab-local`` (gitignored). The tests
SKIP cleanly when the env is not set, so the suite is safe to collect without a
GitLab available.
"""
import os
import pathlib
import sys

import pytest

# Make the backend importable without installing it.
_ROOT = pathlib.Path(__file__).resolve().parents[1]
_BACKEND_SRC = _ROOT / "computor-backend" / "src"
if str(_BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(_BACKEND_SRC))

# Convenience: load a local (gitignored) env file if present.
_ENV_FILE = pathlib.Path(__file__).resolve().parent / ".env.gitlab-local"
if _ENV_FILE.exists():
    for _raw in _ENV_FILE.read_text().splitlines():
        _line = _raw.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: live integration tests (need a real GitLab)"
    )


@pytest.fixture(scope="session")
def gitlab_cfg():
    url = os.environ.get("GITLAB_IT_URL")
    token = os.environ.get("GITLAB_IT_TOKEN")
    parent = os.environ.get("GITLAB_IT_PARENT_GROUP_ID")
    if not (url and token and parent):
        pytest.skip(
            "Set GITLAB_IT_URL / GITLAB_IT_TOKEN / GITLAB_IT_PARENT_GROUP_ID "
            "(or integration-tests/.env.gitlab-local) to run the GitLab integration tests."
        )
    return {"url": url, "token": token, "parent_group_id": int(parent)}


@pytest.fixture(scope="session")
def gitlab_provider(gitlab_cfg):
    from computor_backend.git_provider.gitlab import GitLabProviderClient

    return GitLabProviderClient(gitlab_cfg["url"], gitlab_cfg["token"], None)
