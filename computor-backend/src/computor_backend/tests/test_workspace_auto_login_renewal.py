"""A workspace start renews an auto-login token that no longer works.

Only provisioning minted auto-login tokens, and they expire after
``workspace_token_ttl_days``. Coder carries ``computor_auth_token`` forward on
every start, so a workspace kept its dead token and the extension inside asked
for a browser sign-in it cannot complete there (computor.at, 2026-10-29;
backport of computor-backend#455 to release/2026.10).
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from computor_backend.api import coder as coder_api
from computor_backend.permissions.principal import Principal

OLD = "ctp_" + "a" * 32
NEW = "ctp_" + "b" * 32


def _workspace(build="build-1"):
    return SimpleNamespace(name="vscode", latest_build_id=build, id="ws-1", template_name="vscode-workspace")


def _client(params):
    client = MagicMock()
    client.get_build_params = AsyncMock(return_value=params)
    return client


@pytest.fixture
def owner(monkeypatch):
    monkeypatch.setattr(coder_api, "_computor_user_for_coder_name", lambda *_a: SimpleNamespace(id="owner-id"))
    monkeypatch.setattr(coder_api, "get_cache", lambda: "cache")
    minted = []

    def mint(db, cache, target, by, workspace_name, ttl_days):
        minted.append((target, by, workspace_name, ttl_days))
        return NEW

    monkeypatch.setattr(coder_api, "mint_workspace_token", mint)
    return minted


def _caller(user_id="owner-id"):
    return Principal(user_id=user_id, roles=["_workspace_user"])


async def _params(client, caller=None, workspace=None):
    return await coder_api._auto_login_token_params(
        MagicMock(), client, caller or _caller(), "uowner", workspace or _workspace(), 30)


@pytest.mark.asyncio
async def test_a_valid_token_is_kept(owner, monkeypatch):
    monkeypatch.setattr(coder_api, "_auto_login_token_valid", lambda _db, token: token == OLD)
    assert await _params(_client({"computor_auth_token": OLD})) is None
    assert owner == []


@pytest.mark.asyncio
@pytest.mark.parametrize("carried", [OLD, ""], ids=["revoked-or-expired", "empty"])
async def test_a_dead_token_is_replaced(owner, monkeypatch, carried):
    monkeypatch.setattr(coder_api, "_auto_login_token_valid", lambda *_a: False)
    assert await _params(_client({"computor_auth_token": carried})) == {"computor_auth_token": NEW}
    assert owner == [("owner-id", "owner-id", "vscode", 30)]


@pytest.mark.asyncio
@pytest.mark.parametrize("params", [{}, {"home_mode": "shared"}], ids=["unreadable", "template-without-token"])
async def test_without_the_parameter_nothing_changes(owner, params):
    assert await _params(_client(params)) is None
    assert owner == []


@pytest.mark.asyncio
async def test_no_owner_or_no_build_changes_nothing(owner, monkeypatch):
    client = _client({"computor_auth_token": OLD})
    assert await _params(client, workspace=_workspace(build=None)) is None
    monkeypatch.setattr(coder_api, "_computor_user_for_coder_name", lambda *_a: None)
    assert await _params(client) is None
    assert owner == [] and client.get_build_params.await_count == 0


def _db_with(row):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = row
    return db


@pytest.mark.parametrize("token, row, valid", [
    (OLD, SimpleNamespace(expires_at=None), True),
    (OLD, SimpleNamespace(expires_at=datetime.now(timezone.utc) + timedelta(days=20)), True),
    (OLD, SimpleNamespace(expires_at=datetime.now(timezone.utc) + timedelta(hours=3)), False),
    (OLD, None, False),
    ("not-a-token", SimpleNamespace(expires_at=None), False),
], ids=["no-expiry", "weeks-left", "expires-today", "revoked-or-unknown", "malformed"])
def test_token_validity(token, row, valid):
    assert coder_api._auto_login_token_valid(_db_with(row), token) is valid


@pytest.mark.asyncio
async def test_start_passes_the_new_token(owner, monkeypatch):
    details = MagicMock()
    details.workspace = _workspace()
    client = _client({"computor_auth_token": OLD})
    client.get_workspace = AsyncMock(return_value=details)
    client.ensure_user_active = AsyncMock()
    client.start_workspace = AsyncMock(return_value=True)
    monkeypatch.setattr(coder_api, "_require_verified_workspace_limits", AsyncMock())
    monkeypatch.setattr(coder_api, "_check_workspace_access_or_course_member", lambda *_a, **_k: None)
    monkeypatch.setattr(coder_api, "_enforce_workspace_admission", AsyncMock())
    monkeypatch.setattr(coder_api, "workspace_start_policy", AsyncMock(return_value={}))
    monkeypatch.setattr(coder_api, "_current_app_credential_params", lambda *_a: {"workspace_app_hash": "h"})
    monkeypatch.setattr(coder_api, "_auto_login_token_valid", lambda *_a: False)
    settings = SimpleNamespace(workspace_token_ttl_days=30)

    result = await coder_api.start_workspace("uowner", "vscode", _caller(), settings, client, MagicMock())
    assert result.success is True
    overrides = client.start_workspace.await_args.kwargs["param_overrides"]
    assert overrides == {"workspace_app_hash": "h", "computor_auth_token": NEW}

