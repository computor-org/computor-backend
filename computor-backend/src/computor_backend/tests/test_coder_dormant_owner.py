"""Coder never sees a login when Computor authenticates workspace traffic."""

import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from computor_types.coder import CoderUserCreate

from computor_backend.api import coder as coder_api
from computor_backend.coder import keepalive
from computor_backend.coder.client import CoderClient
from computor_backend.coder.exceptions import CoderAPIError


def _coder_user(status: str) -> dict:
    return {
        "id": "coder-user-id",
        "username": "uowner",
        "email": "owner@example.test",
        "status": status,
    }


def _client(transport: httpx.MockTransport) -> CoderClient:
    client = CoderClient.__new__(CoderClient)
    client.settings = MagicMock(url="http://coder.test", timeout=5, admin_api_secret="")
    client._session_token = "admin-token"
    client._client = httpx.AsyncClient(base_url="http://coder.test", transport=transport)
    client._one_time_user_client = lambda: httpx.AsyncClient(
        base_url="http://coder.test", transport=transport, trust_env=False
    )
    return client


@pytest.mark.asyncio
@pytest.mark.parametrize("initial,activate_calls", [("dormant", 1), ("active", 0), ("suspended", 0)])
async def test_existing_owner_is_usable_without_reactivating_suspensions(initial, activate_calls):
    state = {"status": initial, "activations": 0, "last_seen": False, "issued": 0, "revoked": 0}

    def coder(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/api/v2/users/me":
            assert request.headers["Coder-Session-Token"] == "ephemeral1-secret"
            state["last_seen"] = True
            return httpx.Response(200, json={"id": "coder-user-id"})
        assert request.headers["Coder-Session-Token"] == "admin-token"
        if request.method == "GET" and request.url.path == "/api/v2/users":
            return httpx.Response(200, json={"users": [_coder_user(state["status"])]})
        if request.method == "PUT" and request.url.path == "/api/v2/users/coder-user-id/status/activate":
            state["activations"] += 1
            state["status"] = "active"
            return httpx.Response(200, json=_coder_user("active"))
        if request.method == "POST" and request.url.path == "/api/v2/users/coder-user-id/keys/tokens":
            issued = json.loads(request.content)
            assert issued["lifetime"] == 60_000_000_000  # Coder expects nanoseconds
            assert issued["token_name"].startswith("computor-last-seen-")
            state["issued"] += 1
            return httpx.Response(201, json={"key": "ephemeral1-secret"})
        if request.method == "DELETE" and request.url.path == "/api/v2/users/coder-user-id/keys/ephemeral1":
            state["revoked"] += 1
            return httpx.Response(204)
        raise AssertionError(f"unexpected Coder request {request.method} {request.url.path}")

    client = _client(httpx.MockTransport(coder))
    try:
        user, created = await client.get_or_create_user(
            CoderUserCreate(username="uowner", email="owner@example.test", password="secret-123")
        )
    finally:
        await client.close()
    assert created is False
    assert user.status == ("active" if initial == "dormant" else initial)
    assert state["activations"] == activate_calls
    assert state["last_seen"] is bool(activate_calls)
    assert state["issued"] == state["revoked"] == activate_calls


@pytest.mark.asyncio
@pytest.mark.parametrize("seen_status,seen_user", [(401, "coder-user-id"), (200, "wrong-user")])
async def test_one_time_key_is_revoked_when_activity_touch_fails(seen_status, seen_user):
    revoked = []

    def coder(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "GET" and path == "/api/v2/users/me":
            return httpx.Response(seen_status, json={"id": seen_user})
        if request.method == "POST" and path == "/api/v2/users/coder-user-id/keys/tokens":
            return httpx.Response(201, json={"key": "ephemeral1-secret"})
        if request.method == "DELETE" and path == "/api/v2/users/coder-user-id/keys/ephemeral1":
            revoked.append(True)
            return httpx.Response(204)
        raise AssertionError(f"unexpected Coder request {request.method} {path}")

    client = _client(httpx.MockTransport(coder))
    try:
        with pytest.raises(CoderAPIError):
            await client._mark_user_seen("coder-user-id")
    finally:
        await client.close()
    assert revoked == [True]


@pytest.mark.asyncio
async def test_start_reactivates_owner_before_asking_coder_to_start(monkeypatch):
    state = {"active": False}
    client = MagicMock()
    details = MagicMock()
    details.workspace.template_name = "vscode"
    details.workspace.latest_build_id = "build-id"
    details.workspace.id = "workspace-id"
    client.get_workspace = AsyncMock(return_value=details)

    async def activate(_username):
        state["active"] = True

    async def start(*_args, **_kwargs):
        assert state["active"], "Coder rejects a dormant owner's workspace agent"
        return True

    client.ensure_user_active = AsyncMock(side_effect=activate)
    client.start_workspace = AsyncMock(side_effect=start)
    monkeypatch.setattr(coder_api, "_check_workspace_access_or_course_member", lambda *_a, **_k: None)
    monkeypatch.setattr(coder_api, "_enforce_workspace_admission", AsyncMock())
    monkeypatch.setattr(coder_api, "workspace_start_policy", AsyncMock(return_value={}))
    monkeypatch.setattr(coder_api, "_current_app_credential_params", lambda *_a: {})
    monkeypatch.delenv("COMPUTOR_PUBLIC_DEPLOYMENT", raising=False)

    result = await coder_api.start_workspace("uowner", "vscode", MagicMock(), MagicMock(), client, MagicMock())
    assert result.success is True
    client.ensure_user_active.assert_awaited_once_with("uowner")


@pytest.mark.asyncio
async def test_forwardauth_activity_restores_owner_before_deadline_bump(monkeypatch):
    state = {"active": False}
    client = MagicMock()

    async def activate(_owner):
        state["active"] = True

    async def extend(*_args, **_kwargs):
        assert state["active"], "Coder cannot maintain a dormant owner's agent"
        return True

    client.ensure_user_active = AsyncMock(side_effect=activate)
    client.get_workspace = AsyncMock(return_value=MagicMock(workspace=MagicMock(id="workspace-id")))
    client.extend_workspace_deadline = AsyncMock(side_effect=extend)
    monkeypatch.setattr(keepalive, "get_coder_client", lambda: client)
    keepalive._workspace_ids.clear()
    await keepalive._extend("uowner", "vscode", 3_600_000)
    client.ensure_user_active.assert_awaited_once_with("uowner")
    client.extend_workspace_deadline.assert_awaited_once()
