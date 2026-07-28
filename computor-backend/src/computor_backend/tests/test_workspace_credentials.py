"""Rotating a user's workspace app credential.

The bump is the revocation and must be durable — it is the only part that works
when Coder is down, and a ban depends on it. The push is what makes an already
running workspace stop accepting the old secret.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

import computor_backend.business_logic.workspace_credentials as wc
from computor_backend.coder.naming import encode_coder_username


USER_ID = "0232de59-e05d-4bc2-898f-b879c06abcde"


def _db(version=1):
    """Session mock whose scalar() answers the key-version lookup."""
    db = MagicMock()
    db.query.return_value.filter.return_value.scalar.return_value = version
    return db


def _workspace(name="vscode", running=True, ws_id="ws-1"):
    ws = MagicMock()
    ws.id = ws_id
    ws.name = name
    ws.latest_build_transition = "start" if running else "stop"
    ws.latest_build_status = MagicMock()
    ws.latest_build_status.value = "running" if running else "stopped"
    return ws


# --- the bump (revocation) ----------------------------------------------------


def test_bump_writes_by_id_not_by_mutating_the_user(monkeypatch):
    """UserRepository serves cached rows detached from the session, so a
    rotation that assigned to a User instance would commit nothing at all."""
    monkeypatch.setenv("TOKEN_SECRET", "x" * 32)
    db = _db(version=1)

    version, rotated_at = wc.bump_workspace_app_key_version(db, USER_ID)

    assert version == 2
    assert rotated_at.tzinfo is not None
    db.query.return_value.filter.return_value.update.assert_called_once()
    db.commit.assert_called_once()


def test_bump_does_not_burn_a_version_without_a_token_secret(monkeypatch):
    # Deriving first means a misconfigured deployment fails loudly instead of
    # advancing to a version whose secret nothing can compute.
    monkeypatch.delenv("TOKEN_SECRET", raising=False)
    db = _db(version=1)

    with pytest.raises(RuntimeError):
        wc.bump_workspace_app_key_version(db, USER_ID)

    db.commit.assert_not_called()


def test_bump_evicts_the_cached_user_row(monkeypatch):
    monkeypatch.setenv("TOKEN_SECRET", "x" * 32)
    cache = MagicMock()
    cache.key.return_value = "user:key"

    wc.bump_workspace_app_key_version(_db(version=3), USER_ID, cache)

    cache.delete_by_key.assert_called_once_with("user:key")


def test_a_failing_cache_never_fails_the_rotation(monkeypatch):
    monkeypatch.setenv("TOKEN_SECRET", "x" * 32)
    cache = MagicMock()
    cache.delete_by_key.side_effect = RuntimeError("redis down")

    version, _ = wc.bump_workspace_app_key_version(_db(version=1), USER_ID, cache)

    assert version == 2  # the revocation stands


# --- the push -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_push_rebuilds_running_workspaces_with_the_current_secret(monkeypatch):
    monkeypatch.setenv("TOKEN_SECRET", "x" * 32)
    from computor_backend.coder.service import derive_workspace_app_secret

    db = _db(version=4)
    client = AsyncMock()
    client.get_user_workspaces.return_value = [_workspace()]
    client.rebuild_with_params.return_value = True

    result = await wc.push_workspace_app_credential(db, client, USER_ID)

    # Addressed by the encoded Coder name, not the bare uuid.
    client.get_user_workspaces.assert_awaited_once_with(encode_coder_username(USER_ID))
    _, overrides = client.rebuild_with_params.await_args.args
    assert overrides["workspace_app_secret"] == derive_workspace_app_secret(USER_ID, 4)
    assert overrides["workspace_app_hash"].startswith("$argon2")
    assert result.succeeded == 1 and result.failed == 0
    assert result.pushed is True


@pytest.mark.asyncio
async def test_push_reports_stopped_workspaces_without_starting_them(monkeypatch):
    monkeypatch.setenv("TOKEN_SECRET", "x" * 32)
    db = _db()
    client = AsyncMock()
    client.get_user_workspaces.return_value = [_workspace(running=False)]

    result = await wc.push_workspace_app_credential(db, client, USER_ID)

    client.rebuild_with_params.assert_not_awaited()
    assert result.succeeded == 0 and result.failed == 1
    assert "next start" in result.outcomes[0].error


@pytest.mark.asyncio
async def test_one_broken_workspace_does_not_strand_the_others(monkeypatch):
    monkeypatch.setenv("TOKEN_SECRET", "x" * 32)
    db = _db()
    client = AsyncMock()
    client.get_user_workspaces.return_value = [
        _workspace(name="a", ws_id="ws-a"),
        _workspace(name="b", ws_id="ws-b"),
    ]
    client.rebuild_with_params.side_effect = [RuntimeError("boom"), True]

    result = await wc.push_workspace_app_credential(db, client, USER_ID)

    assert result.succeeded == 1 and result.failed == 1
    assert result.outcomes[0].error == "Rebuild failed"
    assert result.outcomes[1].success is True


@pytest.mark.asyncio
async def test_push_reports_nothing_pushed_when_the_user_has_no_workspaces(monkeypatch):
    monkeypatch.setenv("TOKEN_SECRET", "x" * 32)
    client = AsyncMock()
    client.get_user_workspaces.return_value = []

    result = await wc.push_workspace_app_credential(_db(), client, USER_ID)

    assert result.pushed is False and result.outcomes == []


# --- rotate = bump + push -----------------------------------------------------


@pytest.mark.asyncio
async def test_rotate_bumps_then_pushes(monkeypatch):
    monkeypatch.setenv("TOKEN_SECRET", "x" * 32)
    db = _db(version=1)
    client = AsyncMock()
    client.get_user_workspaces.return_value = [_workspace()]
    client.rebuild_with_params.return_value = True

    result = await wc.rotate_workspace_app_credential(db, client, USER_ID)

    db.commit.assert_called_once()
    assert result.succeeded == 1
    assert result.rotated_at is not None


@pytest.mark.asyncio
async def test_rotate_without_coder_still_revokes(monkeypatch):
    """Coder disabled or unreachable must not block a revocation — the bump
    alone stops the old secret from ever being issued again."""
    monkeypatch.setenv("TOKEN_SECRET", "x" * 32)
    db = _db(version=1)

    result = await wc.rotate_workspace_app_credential(db, None, USER_ID)

    db.commit.assert_called_once()
    assert result.key_version == 2
    assert result.pushed is False
