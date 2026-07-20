"""Unit tests for the hardened workspace auto-login token (mint_workspace_token).

The COMPUTOR_AUTH_TOKEN injected into a Coder workspace is a ctp_ API token. To
limit the blast radius of a leak it is minted with a bounded lifetime and
rotated (old one revoked) on each provision. Tokens are per-workspace
("workspace-auto-login:{name}") so re-provisioning one workspace does not
de-authenticate the user's other workspaces. Rotation is compensable: if the
new token never reaches the workspace, rollback_workspace_token_rotation
revokes it and restores the superseded one (whose plaintext the workspace
still holds). These tests pin that behavior with a mocked DB/repo — no live
database needed.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from computor_backend.coder.service import (
    MintResult,
    mint_workspace_token,
    rollback_workspace_token_rotation,
)
from computor_backend.repositories import DuplicateError


@patch("computor_backend.coder.service.ApiTokenRepository")
def test_mint_sets_bounded_expiry(mock_repo_cls):
    repo = mock_repo_cls.return_value
    repo.find_all_active_by_name.return_value = []
    db = MagicMock()

    result = mint_workspace_token(db, MagicMock(), "user-uuid", "admin-uuid", "python", ttl_days=30)

    assert result is not None and result.token.startswith("ctp_")
    api_token = repo.create.call_args[0][0]
    assert api_token.expires_at is not None
    delta = api_token.expires_at - datetime.now(timezone.utc)
    assert timedelta(days=29) < delta <= timedelta(days=30)
    db.commit.assert_called_once()


@patch("computor_backend.coder.service.ApiTokenRepository")
def test_mint_never_expires_when_ttl_non_positive(mock_repo_cls):
    repo = mock_repo_cls.return_value
    repo.find_all_active_by_name.return_value = []
    db = MagicMock()

    for ttl in (0, None):
        repo.reset_mock()
        mint_workspace_token(db, MagicMock(), "user-uuid", "admin-uuid", "python", ttl_days=ttl)
        api_token = repo.create.call_args[0][0]
        assert api_token.expires_at is None


@patch("computor_backend.coder.service.invalidate_token_cache_sync")
@patch("computor_backend.coder.service.ApiTokenRepository")
def test_mint_rotates_existing_per_workspace_token(mock_repo_cls, mock_invalidate):
    repo = mock_repo_cls.return_value
    existing = MagicMock()
    existing.id = "old-token-id"
    repo.find_all_active_by_name.return_value = [existing]
    revoked = MagicMock()
    revoked.id = "old-token-id"
    revoked.token_hash = b"\xaa\xbb"
    repo.revoke.return_value = revoked
    db = MagicMock()

    result = mint_workspace_token(db, MagicMock(), "user-uuid", "admin-uuid", "python", ttl_days=30)

    # Only THIS workspace's previous token is looked up and revoked.
    repo.find_all_active_by_name.assert_called_once_with("user-uuid", "workspace-auto-login:python")
    repo.revoke.assert_called_once()
    assert repo.revoke.call_args[0][0] == "old-token-id"
    # The revoking admin is recorded for the audit trail.
    assert repo.revoke.call_args.kwargs["revoked_by"] == "admin-uuid"
    # Rotation is compensable: the result names what it replaced.
    assert result.superseded_ids == ["old-token-id"]
    # The rotated-out token is dropped from the auth cache immediately.
    mock_invalidate.assert_called_once_with(b"\xaa\xbb".hex())


@patch("computor_backend.coder.service.invalidate_token_cache_sync")
@patch("computor_backend.coder.service.ApiTokenRepository")
def test_mint_for_legacy_default_workspace_also_revokes_unsuffixed_token(mock_repo_cls, _inv):
    repo = mock_repo_cls.return_value
    legacy = MagicMock()
    legacy.id = "legacy-token-id"

    def lookup(user_id, name):
        return [legacy] if name == "workspace-auto-login" else []

    repo.find_all_active_by_name.side_effect = lookup
    db = MagicMock()

    mint_workspace_token(db, MagicMock(), "user-uuid", "admin-uuid", "workspace", ttl_days=30)

    # Tokens minted before the per-workspace scheme (plain name) belonged to
    # the old default workspace "workspace" — rotated when re-provisioning it.
    names_looked_up = {c.args[1] for c in repo.find_all_active_by_name.call_args_list}
    assert names_looked_up == {"workspace-auto-login:workspace", "workspace-auto-login"}
    repo.revoke.assert_called_once()
    assert repo.revoke.call_args[0][0] == "legacy-token-id"


@patch("computor_backend.coder.service.ApiTokenRepository")
def test_mint_token_is_named_per_workspace(mock_repo_cls):
    repo = mock_repo_cls.return_value
    repo.find_all_active_by_name.return_value = []
    db = MagicMock()

    mint_workspace_token(db, MagicMock(), "user-uuid", "admin-uuid", "python", ttl_days=30)

    api_token = repo.create.call_args[0][0]
    assert api_token.name == "workspace-auto-login:python"
    assert api_token.user_id == "user-uuid"


@patch("computor_backend.coder.service.invalidate_token_cache_sync")
@patch("computor_backend.coder.service.ApiTokenRepository")
def test_mint_retries_once_on_unique_index_conflict(mock_repo_cls, _inv):
    repo = mock_repo_cls.return_value
    competitor = MagicMock()
    competitor.id = "competitor-id"
    # First pass sees no actives (stale view) and hits the active-token unique
    # index; the retry re-reads past the cache, finds the competing mint's
    # token, and rotates it.
    repo.find_all_active_by_name.side_effect = [[], [competitor]]
    repo.create.side_effect = [DuplicateError("ApiToken", {}), None]
    cache = MagicMock()
    db = MagicMock()

    result = mint_workspace_token(db, cache, "user-uuid", "admin-uuid", "python", ttl_days=30)

    assert result is not None and result.token.startswith("ctp_")
    cache.invalidate_tags.assert_called_once_with(
        "api_token:name:user-uuid:workspace-auto-login:python"
    )
    assert repo.revoke.call_args[0][0] == "competitor-id"


@patch("computor_backend.coder.service.invalidate_token_cache_sync")
@patch("computor_backend.coder.service.ApiTokenRepository")
def test_mint_restores_superseded_when_create_fails(mock_repo_cls, mock_invalidate):
    repo = mock_repo_cls.return_value
    old = MagicMock()
    old.id = "old-token-id"
    repo.find_all_active_by_name.return_value = [old]
    revoked = MagicMock()
    revoked.id = "old-token-id"
    revoked.token_hash = b"\xaa"
    repo.revoke.return_value = revoked
    repo.create.side_effect = RuntimeError("db down")
    db = MagicMock()

    result = mint_workspace_token(db, MagicMock(), "user-uuid", "admin-uuid", "python", ttl_days=30)

    # The already-committed revocation is compensated so the running workspace
    # keeps its still-deployed token, and the caller sees a hard failure.
    assert result is None
    repo.unrevoke.assert_called_once_with("old-token-id", unrevoked_by="admin-uuid")
    mock_invalidate.assert_not_called()


@patch("computor_backend.coder.service.invalidate_token_cache_sync")
@patch("computor_backend.coder.service.ApiTokenRepository")
def test_rollback_revokes_new_and_restores_old(mock_repo_cls, mock_invalidate):
    repo = mock_repo_cls.return_value
    revoked_new = MagicMock()
    revoked_new.token_hash = b"\xbb"
    repo.revoke.return_value = revoked_new
    mint_result = MintResult(
        token="ctp_x", new_token_id="new-id", superseded_ids=["old-1", "old-2"]
    )

    rollback_workspace_token_rotation(
        MagicMock(), MagicMock(), mint_result, revoked_by="admin-uuid"
    )

    # New (undelivered) token revoked first, then predecessors restored — the
    # order the active-token unique index requires.
    assert repo.revoke.call_args[0][0] == "new-id"
    assert [c.args[0] for c in repo.unrevoke.call_args_list] == ["old-1", "old-2"]
    mock_invalidate.assert_called_once_with(b"\xbb".hex())


@patch("computor_backend.coder.service.invalidate_token_cache_sync")
@patch("computor_backend.coder.service.ApiTokenRepository")
def test_rollback_skips_restore_when_new_revoke_fails(mock_repo_cls, _inv):
    repo = mock_repo_cls.return_value
    repo.revoke.side_effect = RuntimeError("db down")
    mint_result = MintResult(token="ctp_x", new_token_id="new-id", superseded_ids=["old-1"])

    # Never raises (callers re-raise the provisioning error), and does not try
    # a restore the unique index would reject while the new token is active.
    rollback_workspace_token_rotation(
        MagicMock(), MagicMock(), mint_result, revoked_by="admin-uuid"
    )

    repo.unrevoke.assert_not_called()
