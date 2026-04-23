"""Top-level pytest configuration for the integration test suite.

Fixtures and helpers layer onto this as later milestones land. For M1
this file only ensures the repo root is importable and exposes the
integration-test environment to tests.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
IT_ROOT = Path(__file__).resolve().parent

# Make sibling packages (computor-types, computor-client, etc.) importable
# when tests are run in-tree without installing them.
for pkg in ("computor-types/src", "computor-client/src", "computor-utils/src"):
    candidate = REPO_ROOT / pkg
    if candidate.is_dir() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())


_load_env_file(IT_ROOT / ".env.integration")

# Fixtures published to every test via plugin registration.
pytest_plugins = [
    "fixtures.api",
    "fixtures.db",
    "fixtures.course",
    "fixtures.users",
    "fixtures.clients",
    "fixtures.permission_matrix",
    "reporting",
]


@pytest.fixture(scope="session")
def it_env() -> dict[str, str]:
    """Snapshot of integration-test env vars, for tests that need them."""
    return dict(os.environ)


@pytest.fixture(scope="session")
def api_base_url() -> str:
    port = os.environ.get("IT_API_PORT", "18000")
    return f"http://localhost:{port}"


@pytest.fixture(scope="session")
def gitlab_base_url() -> str:
    port = os.environ.get("IT_GITLAB_HTTP_PORT", "8085")
    return f"http://localhost:{port}"
