"""Smoke: every service we rely on answers on its published port.

Fills out as later milestones land (assertions on /openapi.json content,
Temporal workflow list, MinIO bucket existence, etc.). For M1 we just
prove the stack is up.
"""

from __future__ import annotations

import os

import httpx
import pytest

pytestmark = pytest.mark.smoke


def test_api_docs_reachable(api_base_url: str) -> None:
    r = httpx.get(f"{api_base_url}/docs", timeout=10)
    assert r.status_code == 200, r.text


def test_api_openapi_reachable(api_base_url: str) -> None:
    r = httpx.get(f"{api_base_url}/openapi.json", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert "paths" in data and data["paths"], "OpenAPI advertises no paths"


def test_gitlab_health(gitlab_base_url: str) -> None:
    r = httpx.get(f"{gitlab_base_url}/-/health", timeout=10)
    assert r.status_code == 200, r.text


def test_gitlab_api_reachable(gitlab_base_url: str) -> None:
    token = os.environ.get("GITLAB_ADMIN_TOKEN", "")
    if not token:
        pytest.skip("GITLAB_ADMIN_TOKEN not set — run `make bootstrap`.")
    r = httpx.get(
        f"{gitlab_base_url}/api/v4/user",
        headers={"PRIVATE-TOKEN": token},
        timeout=10,
    )
    assert r.status_code == 200
    assert r.json().get("username") == "root"


def test_minio_health() -> None:
    port = os.environ.get("IT_MINIO_API_PORT", "19000")
    r = httpx.get(f"http://localhost:{port}/minio/health/live", timeout=10)
    assert r.status_code == 200


def test_temporal_ui_reachable() -> None:
    port = os.environ.get("IT_TEMPORAL_UI_PORT", "18088")
    r = httpx.get(f"http://localhost:{port}/", timeout=10)
    assert r.status_code == 200
