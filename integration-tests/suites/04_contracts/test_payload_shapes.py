"""Happy-path payload contracts — the shape/invariants of success responses."""

from __future__ import annotations

import httpx
import pytest

pytestmark = [pytest.mark.contracts]


def test_invite_create_shape(admin_client: httpx.Client) -> None:
    r = admin_client.post(
        "/admin/invites",
        json={"max_uses": 3, "expires_in_days": 7, "roles": ["_user_manager"], "note": "shape"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["token"]
    assert body["max_uses"] == 3
    assert body["use_count"] == 0
    assert body["revoked_at"] is None
    assert body["expires_at"]
    assert "_user_manager" in body["roles"]


def test_public_invite_metadata_hides_nothing_sensitive(
    admin_client: httpx.Client, api_base_url: str
) -> None:
    token = admin_client.post(
        "/admin/invites", json={"max_uses": 1, "expires_in_days": 7, "roles": ["_user_manager"]}
    ).json()["token"]
    r = httpx.get(f"{api_base_url}/invites/{token}", timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "_user_manager" in body.get("roles", [])
    assert body.get("expires_at")
    # The public view must not leak the raw token back.
    assert "token" not in body or body.get("token") in (None, "")


def test_course_git_binding_shape(target_course_git: dict) -> None:
    binding = target_course_git
    assert binding["delivery"] == "git"
    assert binding["student_repo_modes"] == ["managed"]
    assert binding["locked"] is True
    # Token is stored encrypted and never returned; URLs are the public host.
    assert binding["has_token"] is False
    url = binding.get("template_url") or ""
    assert url.startswith("http://localhost:"), url
    assert "forgejo:3030" not in url


def test_provisioned_repo_shape(provisioned_repos: dict) -> None:
    repo = provisioned_repos["s_correct"]
    assert repo["mode"] == "managed"
    assert repo["provider_type"] == "forgejo"
    assert repo["clone_token"]  # one-time token present on provision
    assert repo["http_url"].startswith("http://localhost:")
    assert "forgejo:3030" not in repo["http_url"]
