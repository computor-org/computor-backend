"""Unit tests for the hardened workspace auto-login token (mint_workspace_token).

The COMPUTOR_AUTH_TOKEN injected into a Coder workspace is a ctp_ API token. To
limit the blast radius of a leak it is minted with a bounded lifetime and
rotated (old one revoked) on each provision. Tokens are per-workspace
("workspace-auto-login:{name}") so re-provisioning one workspace does not
de-authenticate the user's other workspaces. These tests pin that behavior with
a mocked DB/repo — no live database needed.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from computor_backend.coder.service import mint_workspace_token

import pytest

# Quarantined from the default run — Coder feature is out of testing scope
# (run with -m coder). These are mocked unit tests, but the feature is excluded.
pytestmark = pytest.mark.coder


@patch("computor_backend.coder.service.ApiTokenRepository")
def test_mint_sets_bounded_expiry(mock_repo_cls):
    mock_repo_cls.return_value.find_all_active_by_name.return_value = []
    db = MagicMock()

    token = mint_workspace_token(db, MagicMock(), "user-uuid", "admin-uuid", "python", ttl_days=30)

    assert token and token.startswith("ctp_")
    api_token = db.add.call_args[0][0]
    assert api_token.expires_at is not None
    delta = api_token.expires_at - datetime.now(timezone.utc)
    assert timedelta(days=29) < delta <= timedelta(days=30)
    db.commit.assert_called_once()


@patch("computor_backend.coder.service.ApiTokenRepository")
def test_mint_never_expires_when_ttl_non_positive(mock_repo_cls):
    mock_repo_cls.return_value.find_all_active_by_name.return_value = []
    db = MagicMock()

    for ttl in (0, None):
        db.reset_mock()
        mint_workspace_token(db, MagicMock(), "user-uuid", "admin-uuid", "python", ttl_days=ttl)
        api_token = db.add.call_args[0][0]
        assert api_token.expires_at is None


@patch("computor_backend.coder.service.ApiTokenRepository")
def test_mint_rotates_existing_per_workspace_token(mock_repo_cls):
    repo = mock_repo_cls.return_value
    existing = MagicMock()
    existing.id = "old-token-id"
    repo.find_all_active_by_name.return_value = [existing]
    db = MagicMock()

    mint_workspace_token(db, MagicMock(), "user-uuid", "admin-uuid", "python", ttl_days=30)

    # Only THIS workspace's previous token is looked up and revoked.
    repo.find_all_active_by_name.assert_called_once_with("user-uuid", "workspace-auto-login:python")
    repo.revoke.assert_called_once()
    assert repo.revoke.call_args[0][0] == "old-token-id"


@patch("computor_backend.coder.service.ApiTokenRepository")
def test_mint_for_legacy_default_workspace_also_revokes_unsuffixed_token(mock_repo_cls):
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
    mock_repo_cls.return_value.find_all_active_by_name.return_value = []
    db = MagicMock()

    mint_workspace_token(db, MagicMock(), "user-uuid", "admin-uuid", "python", ttl_days=30)

    api_token = db.add.call_args[0][0]
    assert api_token.name == "workspace-auto-login:python"
    assert api_token.user_id == "user-uuid"
