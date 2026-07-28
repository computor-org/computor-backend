"""Banning a user revokes their workspace app credential.

A ban blocks authentication, so the banned user's browser can no longer reach a
workspace through the proxy. Their running workspaces keep serving their apps
on the workspace bridge though, to anything holding the credential — which the
banned user may. So the ban rotates it.

The rotation must never be able to fail the ban: revoking access is the urgent
part, re-keying containers is not.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from computor_backend.api.user_ban import _revoke_workspace_app_credential


USER_ID = "0232de59-e05d-4bc2-898f-b879c06abcde"


def _user():
    user = MagicMock()
    user.id = USER_ID
    return user


def _rotation_result(version=2, succeeded=1, failed=0):
    return MagicMock(key_version=version, succeeded=succeeded, failed=failed)


@pytest.mark.asyncio
async def test_ban_rotates_the_credential_when_coder_is_enabled():
    rotate = AsyncMock(return_value=_rotation_result())
    with patch("computor_backend.business_logic.workspace_credentials"
               ".rotate_workspace_app_credential", rotate), \
         patch("computor_backend.coder.config.get_coder_settings",
               return_value=MagicMock(enabled=True)), \
         patch("computor_backend.coder.client.get_coder_client",
               return_value=MagicMock()):
        await _revoke_workspace_app_credential(MagicMock(), _user())

    rotate.assert_awaited_once()
    assert rotate.await_args.args[2] == USER_ID


@pytest.mark.asyncio
async def test_ban_still_rotates_with_coder_disabled():
    # The bump is pure database work; it is the durable half of the revocation
    # and must happen whether or not there is a Coder to push to.
    rotate = AsyncMock(return_value=_rotation_result(succeeded=0))
    with patch("computor_backend.business_logic.workspace_credentials"
               ".rotate_workspace_app_credential", rotate), \
         patch("computor_backend.coder.config.get_coder_settings",
               return_value=MagicMock(enabled=False)):
        await _revoke_workspace_app_credential(MagicMock(), _user())

    rotate.assert_awaited_once()
    assert rotate.await_args.args[1] is None  # no client constructed


@pytest.mark.asyncio
async def test_a_broken_coder_does_not_fail_the_ban():
    rotate = AsyncMock(side_effect=RuntimeError("coder is on fire"))
    with patch("computor_backend.business_logic.workspace_credentials"
               ".rotate_workspace_app_credential", rotate), \
         patch("computor_backend.coder.config.get_coder_settings",
               return_value=MagicMock(enabled=True)), \
         patch("computor_backend.coder.client.get_coder_client",
               return_value=MagicMock()):
        # Must return normally: the caller has already stamped banned_at and
        # set the Redis kill-switch, and that is what actually blocks the user.
        await _revoke_workspace_app_credential(MagicMock(), _user())


@pytest.mark.asyncio
async def test_a_missing_token_secret_does_not_fail_the_ban():
    rotate = AsyncMock(side_effect=RuntimeError("TOKEN_SECRET is not set"))
    with patch("computor_backend.business_logic.workspace_credentials"
               ".rotate_workspace_app_credential", rotate), \
         patch("computor_backend.coder.config.get_coder_settings",
               return_value=MagicMock(enabled=True)), \
         patch("computor_backend.coder.client.get_coder_client",
               return_value=MagicMock()):
        await _revoke_workspace_app_credential(MagicMock(), _user())
