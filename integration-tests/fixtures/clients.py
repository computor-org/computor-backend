"""Session-scoped HTTP clients for each course role.

Each role logs in exactly once per session (the `/auth/login` endpoint is
rate-limited to 5/min per username, so re-logging-in in a fixture loop is
unsafe). The bearer token is cached on the fixture and the `httpx.Client`
reuses it for every request.

The fixtures build on `seed_role_users` from `fixtures.users`, which in turn
drives the `target_course` hierarchy. `admin_client` and `anonymous_client`
live in `fixtures.api` and are not re-exported here.
"""

from __future__ import annotations

from typing import Iterator

import httpx
import pytest

from fixtures.api import DEFAULT_TIMEOUT


def _login_bearer(api_base_url: str, username: str, password: str) -> str:
    with httpx.Client(base_url=api_base_url, timeout=DEFAULT_TIMEOUT) as c:
        r = c.post("/auth/login", json={"username": username, "password": password})
        r.raise_for_status()
        token = r.json()["access_token"]
    assert isinstance(token, str) and token, "login returned empty access_token"
    return token


def _bearer_session_client(
    api_base_url: str, username: str, password: str
) -> Iterator[httpx.Client]:
    token = _login_bearer(api_base_url, username, password)
    with httpx.Client(
        base_url=api_base_url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=DEFAULT_TIMEOUT,
    ) as client:
        yield client


@pytest.fixture(scope="session")
def owner_client(
    api_base_url: str, seed_role_users: dict[str, dict]
) -> Iterator[httpx.Client]:
    u = seed_role_users["_owner"]
    yield from _bearer_session_client(api_base_url, u["username"], u["password"])


@pytest.fixture(scope="session")
def maintainer_client(
    api_base_url: str, seed_role_users: dict[str, dict]
) -> Iterator[httpx.Client]:
    u = seed_role_users["_maintainer"]
    yield from _bearer_session_client(api_base_url, u["username"], u["password"])


@pytest.fixture(scope="session")
def lecturer_client(
    api_base_url: str, seed_role_users: dict[str, dict]
) -> Iterator[httpx.Client]:
    u = seed_role_users["_lecturer"]
    yield from _bearer_session_client(api_base_url, u["username"], u["password"])


@pytest.fixture(scope="session")
def tutor_client(
    api_base_url: str, seed_role_users: dict[str, dict]
) -> Iterator[httpx.Client]:
    u = seed_role_users["_tutor"]
    yield from _bearer_session_client(api_base_url, u["username"], u["password"])


@pytest.fixture(scope="session")
def student_client(
    api_base_url: str, seed_role_users: dict[str, dict]
) -> Iterator[httpx.Client]:
    u = seed_role_users["_student"]
    yield from _bearer_session_client(api_base_url, u["username"], u["password"])
