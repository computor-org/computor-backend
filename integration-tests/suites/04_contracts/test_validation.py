"""Payload validation contracts — malformed requests → 400 VAL_001.

Request-validation failures are normalized to HTTP 400 with error_code VAL_001
(not FastAPI's default 422); see computor_backend/exceptions/error_handlers.py.
"""

from __future__ import annotations

import httpx
import pytest

from helpers.assertions import assert_error

pytestmark = [pytest.mark.contracts]


@pytest.mark.parametrize(
    "body",
    [
        {"max_uses": 0, "expires_in_days": 7, "roles": []},      # below min
        {"max_uses": 101, "expires_in_days": 7, "roles": []},    # above max
        {"max_uses": 1, "expires_in_days": 366, "roles": []},    # expiry above max
    ],
    ids=["max_uses=0", "max_uses=101", "expires=366"],
)
def test_invite_bounds_rejected(admin_client: httpx.Client, body: dict) -> None:
    assert_error(admin_client.post("/admin/invites", json=body), 400, "VAL_001")


def test_organization_invalid_ltree_path_rejected(admin_client: httpx.Client) -> None:
    r = admin_client.post(
        "/organizations",
        json={"path": "bad path!", "organization_type": "organization", "title": "X"},
    )
    assert_error(r, 400, "VAL_001")


def test_empty_invite_body_is_valid(admin_client: httpx.Client) -> None:
    # All invite fields default, so an empty body is a valid create (documents
    # that VAL_001 is about constraint violations, not missing optionals).
    r = admin_client.post("/admin/invites", json={})
    assert r.status_code == 201, r.text
