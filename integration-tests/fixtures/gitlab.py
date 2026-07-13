"""Fixtures for the managed-GitLab provisioning tests (``GitLabProviderClient``).

These talk to a real GitLab configured via env, so they work against either the
compose GitLab or a standalone one (e.g. ``../gitlab-local-test`` on :8086):

    GITLAB_IT_URL, GITLAB_IT_TOKEN, GITLAB_IT_PARENT_GROUP_ID

(or ``integration-tests/.env.gitlab-local``). Tests SKIP cleanly when unset.

Unlike the black-box suites, these import the backend's provider client directly,
so this module puts ``computor-backend/src`` on the path at import time.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_IT_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_SRC = _IT_ROOT.parent / "computor-backend" / "src"
if str(_BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(_BACKEND_SRC))

# Load the local (gitignored) GitLab config if present.
_ENV = _IT_ROOT / ".env.gitlab-local"
if _ENV.exists():
    for _raw in _ENV.read_text().splitlines():
        _line = _raw.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())


@pytest.fixture(scope="session")
def gitlab_cfg() -> dict:
    url = os.environ.get("GITLAB_IT_URL")
    token = os.environ.get("GITLAB_IT_TOKEN")
    parent = os.environ.get("GITLAB_IT_PARENT_GROUP_ID")
    if not (url and token and parent):
        pytest.skip(
            "Set GITLAB_IT_URL / GITLAB_IT_TOKEN / GITLAB_IT_PARENT_GROUP_ID "
            "(or integration-tests/.env.gitlab-local) to run the GitLab provider tests."
        )
    return {"url": url, "token": token, "parent_group_id": int(parent)}


@pytest.fixture(scope="session")
def gitlab_provider(gitlab_cfg):
    from computor_backend.git_provider.gitlab import GitLabProviderClient

    return GitLabProviderClient(gitlab_cfg["url"], gitlab_cfg["token"], None)
