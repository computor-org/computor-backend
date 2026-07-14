"""Unit tests for the Coder ForwardAuth endpoint (verify_coder_access).

Covers the workspace-access authorization gate Traefik calls before forwarding to a
code-server workspace, including the admin bypass that lets the shared admin/service
account (Coder username "admin", not the u{uuid} form) reach its workspace.
"""

import json

import pytest

from computor_backend.api.auth import verify_coder_access
from computor_backend.permissions.principal import Principal

# Quarantined from the default run — requires a live Coder (run with -m coder).
pytestmark = pytest.mark.coder


class _FakeURL:
    def __init__(self, path):
        self.path = path


class _FakeRequest:
    """Minimal stand-in for starlette Request: only .headers and .url are used."""

    def __init__(self, forwarded_uri, path="/"):
        self.headers = {"X-Forwarded-Uri": forwarded_uri}
        self.url = _FakeURL(path)


# A backend user UUID and the Coder username derived from it (u + uuid).
USER_UUID = "0232de59-e05d-4bc2-898f-b879c06abcde"
USER_OWNER = "u" + USER_UUID


def _admin():
    return Principal(user_id="admin-backend-uuid", roles=["_admin"])


def _user(uuid=USER_UUID):
    return Principal(user_id=uuid)  # is_admin stays False


def _body(resp):
    return json.loads(resp.body)


@pytest.mark.asyncio
async def test_admin_can_access_admin_owned_workspace():
    # The case that used to 403 with "Invalid workspace URL format".
    resp = await verify_coder_access(_FakeRequest("/coder/admin/workspace/"), _admin())
    assert resp.status_code == 200
    assert _body(resp)["status"] == "authorized"


@pytest.mark.asyncio
async def test_admin_can_access_any_user_workspace():
    resp = await verify_coder_access(_FakeRequest("/coder/%s/workspace/" % USER_OWNER), _admin())
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_user_can_access_own_workspace():
    resp = await verify_coder_access(_FakeRequest("/coder/%s/workspace/" % USER_OWNER), _user())
    assert resp.status_code == 200
    assert _body(resp)["workspace"] == "workspace"


@pytest.mark.asyncio
async def test_user_can_access_own_workspace_when_coder_truncates_username():
    # Coder truncates long usernames; the URL owner is a prefix of the real UUID.
    truncated = "u" + USER_UUID[:20]
    resp = await verify_coder_access(_FakeRequest("/coder/%s/workspace/" % truncated), _user())
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_user_cannot_access_other_users_workspace():
    other = "u" + "ffffffff-ffff-ffff-ffff-ffffffffffff"
    resp = await verify_coder_access(_FakeRequest("/coder/%s/workspace/" % other), _user())
    assert resp.status_code == 403
    assert "not authorized" in _body(resp)["detail"].lower()


@pytest.mark.asyncio
async def test_non_admin_cannot_access_admin_workspace():
    # Non-admin hitting /coder/admin/...: owner is not the u{uuid} form -> denied.
    resp = await verify_coder_access(_FakeRequest("/coder/admin/workspace/"), _user())
    assert resp.status_code == 403
    assert "not authorized" in _body(resp)["detail"].lower()


@pytest.mark.asyncio
async def test_malformed_url_is_rejected():
    # No workspace segment -> doesn't match the path shape.
    resp = await verify_coder_access(_FakeRequest("/coder/onlyowner"), _user())
    assert resp.status_code == 403
    assert _body(resp)["detail"] == "Invalid workspace URL format"
