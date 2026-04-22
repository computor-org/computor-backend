"""HTTP client fixtures.

No per-test reset: the admin session is established once per pytest
session, tokens/cookies accumulate, and teardown is the stack wipe. This
matches the real-run semantics agreed on in issue #106.
"""

from __future__ import annotations

import os
from typing import Iterator

import httpx
import pytest

DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


@pytest.fixture(scope="session")
def admin_credentials() -> dict[str, str]:
    return {
        "username": os.environ["API_ADMIN_USER"],
        "password": os.environ["API_ADMIN_PASSWORD"],
    }


@pytest.fixture(scope="session")
def anonymous_client(api_base_url: str) -> Iterator[httpx.Client]:
    with httpx.Client(base_url=api_base_url, timeout=DEFAULT_TIMEOUT) as client:
        yield client


@pytest.fixture(scope="session")
def admin_basic_client(
    api_base_url: str, admin_credentials: dict[str, str]
) -> Iterator[httpx.Client]:
    auth = httpx.BasicAuth(admin_credentials["username"], admin_credentials["password"])
    with httpx.Client(base_url=api_base_url, auth=auth, timeout=DEFAULT_TIMEOUT) as client:
        yield client


@pytest.fixture(scope="session")
def admin_login(
    anonymous_client: httpx.Client, admin_credentials: dict[str, str]
) -> dict[str, object]:
    """POST /auth/login with admin creds; returns the parsed response body."""
    r = anonymous_client.post("/auth/login", json=admin_credentials)
    r.raise_for_status()
    return r.json()


@pytest.fixture(scope="session")
def admin_access_token(admin_login: dict[str, object]) -> str:
    return admin_login["access_token"]  # type: ignore[return-value]


@pytest.fixture(scope="session")
def admin_refresh_token(admin_login: dict[str, object]) -> str:
    return admin_login["refresh_token"]  # type: ignore[return-value]


@pytest.fixture(scope="session")
def admin_client(
    api_base_url: str, admin_access_token: str
) -> Iterator[httpx.Client]:
    headers = {"Authorization": f"Bearer {admin_access_token}"}
    with httpx.Client(base_url=api_base_url, headers=headers, timeout=DEFAULT_TIMEOUT) as client:
        yield client


def bearer_client(api_base_url: str, token: str) -> httpx.Client:
    """Helper: build a client authed with an arbitrary bearer token."""
    return httpx.Client(
        base_url=api_base_url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=DEFAULT_TIMEOUT,
    )


def api_token_client(api_base_url: str, api_token: str) -> httpx.Client:
    """Helper: build a client authed with an X-API-Token (ctp_*) header."""
    return httpx.Client(
        base_url=api_base_url,
        headers={"X-API-Token": api_token},
        timeout=DEFAULT_TIMEOUT,
    )
