"""Unit tests for the hardened workspace auto-login token (mint_workspace_token).

The COMPUTOR_AUTH_TOKEN injected into a Coder workspace is a ctp_ API token. To
limit the blast radius of a leak it is now minted with a bounded lifetime and
rotated (old one revoked) on each provision. These tests pin that behavior with a
mocked DB/repo — no live database needed.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from computor_backend.coder.service import mint_workspace_token


@patch("computor_backend.coder.service.ApiTokenRepository")
def test_mint_sets_bounded_expiry(mock_repo_cls):
    mock_repo_cls.return_value.find_all_active_by_name.return_value = []
    db = MagicMock()

    token = mint_workspace_token(db, MagicMock(), "user-uuid", "admin-uuid", ttl_days=30)

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
        mint_workspace_token(db, MagicMock(), "user-uuid", "admin-uuid", ttl_days=ttl)
        api_token = db.add.call_args[0][0]
        assert api_token.expires_at is None


@patch("computor_backend.coder.service.ApiTokenRepository")
def test_mint_rotates_existing_singleton(mock_repo_cls):
    repo = mock_repo_cls.return_value
    existing = MagicMock()
    existing.id = "old-token-id"
    repo.find_all_active_by_name.return_value = [existing]
    db = MagicMock()

    mint_workspace_token(db, MagicMock(), "user-uuid", "admin-uuid", ttl_days=30)

    # The previous workspace token is revoked before the new one is issued.
    repo.revoke.assert_called_once()
    assert repo.revoke.call_args[0][0] == "old-token-id"


@patch("computor_backend.coder.service.ApiTokenRepository")
def test_mint_token_is_named_workspace_auto_login(mock_repo_cls):
    mock_repo_cls.return_value.find_all_active_by_name.return_value = []
    db = MagicMock()

    mint_workspace_token(db, MagicMock(), "user-uuid", "admin-uuid", ttl_days=30)

    api_token = db.add.call_args[0][0]
    assert api_token.name == "workspace-auto-login"
    assert api_token.user_id == "user-uuid"
