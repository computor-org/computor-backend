"""HTTP client fixtures.

Auth is SSO-only now (local password login was removed from the backend), so
the admin session is established via the headless Keycloak dance in
`fixtures.keycloak_auth`. No per-test reset: the admin session is established
once per pytest session, state accumulates, and teardown is the stack wipe —
matching the real-run semantics agreed on in issue #106.
"""

from __future__ import annotations

import os
from typing import Iterator

import httpx
import pytest

from fixtures.keycloak_auth import authenticate

DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


@pytest.fixture(scope="session")
def admin_credentials() -> dict[str, str]:
    """The env-bootstrapped admin's Keycloak login (email + password)."""
    return {
        "email": os.environ.get("API_ADMIN_EMAIL", "admin@integration.test"),
        "password": os.environ["API_ADMIN_PASSWORD"],
    }


@pytest.fixture(scope="session")
def anonymous_client(api_base_url: str) -> Iterator[httpx.Client]:
    with httpx.Client(base_url=api_base_url, timeout=DEFAULT_TIMEOUT) as client:
        yield client


@pytest.fixture(scope="session")
def admin_credentials_obj(api_base_url: str, admin_credentials: dict[str, str]):
    """The admin's SSO credentials (token/refresh/user_id), logged in once."""
    return authenticate(
        admin_credentials["email"], admin_credentials["password"], api_base=api_base_url
    )


@pytest.fixture(scope="session")
def admin_access_token(admin_credentials_obj) -> str:
    return admin_credentials_obj.token


@pytest.fixture(scope="session")
def admin_refresh_token(admin_credentials_obj) -> str | None:
    return admin_credentials_obj.refresh_token


@pytest.fixture(scope="session")
def admin_client(api_base_url: str, admin_access_token: str) -> Iterator[httpx.Client]:
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
