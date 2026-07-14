"""Forgejo admin API client — assert git-side state (template/student repos).

Talks to Forgejo directly over its published port with the admin basic-auth
credentials the backend also uses (GIT_SERVER_ADMIN_USERNAME/PASSWORD). Replaces
the removed GitLab provider fixture.
"""

from __future__ import annotations

import os
from typing import Iterator

import httpx
import pytest


def _forgejo_base() -> str:
    return f"http://localhost:{os.environ.get('IT_FORGEJO_PORT', '13030')}"


@pytest.fixture(scope="session")
def forgejo_admin() -> Iterator[httpx.Client]:
    user = os.environ["GIT_SERVER_ADMIN_USERNAME"]
    pw = os.environ["GIT_SERVER_ADMIN_PASSWORD"]
    with httpx.Client(base_url=_forgejo_base(), auth=(user, pw), timeout=30.0) as client:
        yield client


def repo_exists(forgejo_admin: httpx.Client, owner_repo: str) -> bool:
    """owner_repo like 'it_org-it_course_py/template'."""
    return forgejo_admin.get(f"/api/v1/repos/{owner_repo}").status_code == 200


def list_repo_paths(
    forgejo_admin: httpx.Client, owner_repo: str, path: str = "", ref: str = "main"
) -> list[str]:
    """Top-level entries under `path` in the repo (non-recursive)."""
    r = forgejo_admin.get(
        f"/api/v1/repos/{owner_repo}/contents/{path}".rstrip("/"), params={"ref": ref}
    )
    if r.status_code != 200:
        return []
    return [item["path"] for item in r.json()]


def repo_tree(forgejo_admin: httpx.Client, owner_repo: str, ref: str = "main") -> list[str]:
    """Full recursive file list of the repo (git tree)."""
    r = forgejo_admin.get(
        f"/api/v1/repos/{owner_repo}/git/trees/{ref}", params={"recursive": "true"}
    )
    if r.status_code != 200:
        return []
    return [e["path"] for e in r.json().get("tree", []) if e.get("type") == "blob"]
