"""Domain-exception contracts — business-rule violations and their error codes."""

from __future__ import annotations

import httpx
import pytest

from fixtures.examples import ExampleFixture, upload_example
from helpers.assertions import assert_error

pytestmark = [pytest.mark.contracts]


# ---- auth (401 via `detail`, no error_code) ------------------------------

@pytest.mark.parametrize(
    "headers",
    [{"Authorization": "Bearer not-a-real-token"}, {"X-API-Token": "ctp_short"}, {}],
    ids=["bogus-bearer", "malformed-ctp", "unauthenticated"],
)
def test_unauthenticated_requests_401(api_base_url: str, headers: dict) -> None:
    assert_error(httpx.get(f"{api_base_url}/user", headers=headers, timeout=15), 401)


# ---- invite redemption ---------------------------------------------------

def test_accept_unknown_invite_token_404(anonymous_client: httpx.Client) -> None:
    r = anonymous_client.post(
        "/invites/deadbeef-not-a-real-token/accept",
        json={"given_name": "A", "family_name": "B",
              "email": "nope@integration.test", "password": "it-nope-Pass-2099"},
    )
    assert_error(r, 404)


def test_public_get_unknown_invite_404(anonymous_client: httpx.Client) -> None:
    assert_error(anonymous_client.get("/invites/deadbeef-not-a-real-token"), 404)


def test_revoked_invite_cannot_be_accepted(
    admin_client: httpx.Client, api_base_url: str
) -> None:
    created = admin_client.post("/admin/invites", json={"max_uses": 1, "expires_in_days": 7})
    assert created.status_code == 201, created.text
    invite = created.json()
    assert admin_client.delete(f"/admin/invites/{invite['id']}").status_code == 204
    r = httpx.post(
        f"{api_base_url}/invites/{invite['token']}/accept",
        json={"given_name": "R", "family_name": "V",
              "email": "revoked@integration.test", "password": "it-rev-Pass-2099"},
        timeout=15,
    )
    assert r.status_code in (400, 403, 404, 410), r.text


# ---- hierarchy delete guard (bottom-up) ----------------------------------

def test_delete_organization_with_children_409(
    admin_client: httpx.Client, target_course: dict, target_organization: dict
) -> None:
    # target_course pulls in the whole hierarchy; the org still has a family.
    r = admin_client.delete(f"/organizations/{target_organization['id']}")
    assert_error(r, 409, "CONFLICT_001")


# ---- course git binding is immutable once materialized -------------------

def test_rebind_locked_course_git_409(
    admin_client: httpx.Client, target_course: dict, target_course_git: dict, managed_git_server_id: str
) -> None:
    r = admin_client.put(
        f"/courses/{target_course['id']}/git",
        json={"delivery": "git", "git_server_id": managed_git_server_id,
              "student_repo_modes": ["managed"]},
    )
    assert_error(r, 409, "CONFLICT_001")


# ---- example version conflict --------------------------------------------

def test_reupload_same_version_conflict(
    exma_client: httpx.Client,
    example_repository_id: str,
    uploaded_examples: dict,
    python_examples: tuple[ExampleFixture, ...],
) -> None:
    # uploaded_examples already put v1.0.0 in place; re-uploading the same tag conflicts.
    r = upload_example(exma_client, example_repository_id, python_examples[0])
    assert_error(r, 400, "VERSION_001")
