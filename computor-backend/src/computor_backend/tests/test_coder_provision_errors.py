"""Regression tests for error handling in the Coder workspace-provision endpoint.

Production hit `NameError: name 'HTTPException' is not defined` from the endpoint's
`except HTTPException:` clause (HTTPException was never imported), which masked the
real 503 ("template not yet available"). The clause now catches ComputorException —
typed exceptions propagate untouched; unexpected ones are mapped by _handle_coder_error.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from computor_backend.api.coder import provision_workspace
from computor_backend.coder.client import CoderClient
from computor_backend.coder.exceptions import (
    CoderNotFoundError,
    CoderTemplateNotFoundError,
    CoderConnectionError,
    CoderWorkspaceActionError,
)
from computor_backend.coder.service import MintResult
from computor_backend.exceptions import (
    InternalServerException,
    ServiceUnavailableException,
)
from computor_backend.permissions.principal import Principal
from computor_types.workspace_roles import WorkspaceProvisionRequest


def _admin():
    return Principal(user_id="u1", roles=["_admin"])


def _settings():
    # The endpoint reads settings.default_template when the request omits one.
    settings = MagicMock()
    settings.default_template = "python-workspace"
    return settings


@pytest.mark.asyncio
async def test_template_not_found_propagates_as_service_unavailable():
    request = WorkspaceProvisionRequest()  # template omitted -> settings default
    client = MagicMock()
    client.get_template_id = AsyncMock(side_effect=CoderTemplateNotFoundError("python-workspace"))

    with patch("computor_backend.api.coder._check_workspace_access"):
        with pytest.raises(ServiceUnavailableException) as exc:
            await provision_workspace(request, _admin(), _settings(), client, MagicMock(), MagicMock())

    # The typed 503 (not a NameError, not a generic 500) reaches the caller intact.
    assert "not yet available" in str(exc.value)


@pytest.mark.asyncio
async def test_unexpected_coder_error_is_mapped_not_nameerror():
    request = WorkspaceProvisionRequest()
    client = MagicMock()
    client.get_template_id = AsyncMock(side_effect=CoderConnectionError("down"))

    with patch("computor_backend.api.coder._check_workspace_access"):
        with pytest.raises(ServiceUnavailableException) as exc:
            await provision_workspace(request, _admin(), _settings(), client, MagicMock(), MagicMock())

    # Mapped by _handle_coder_error (the `except Exception` path), not a NameError.
    assert "connect to Coder" in str(exc.value)


def _provisionable_client():
    """Client mock that passes every check up to the mint/provision step."""
    client = MagicMock()
    client.get_template_id = AsyncMock(return_value="tid")
    # No Coder user yet -> quota exclusion lookup is skipped.
    client._find_user_by_email = AsyncMock(side_effect=CoderNotFoundError("User", "s@example.org"))
    client.provision_workspace = AsyncMock(return_value=MagicMock())
    return client


@pytest.mark.asyncio
async def test_mint_failure_aborts_provision_with_503():
    request = WorkspaceProvisionRequest()
    client = _provisionable_client()

    with patch("computor_backend.api.coder._check_workspace_access"), \
         patch("computor_backend.api.coder._enforce_template_quota", AsyncMock()), \
         patch("computor_backend.api.coder.get_user_by_id", return_value=MagicMock(id="u1")), \
         patch("computor_backend.api.coder.mint_workspace_token", return_value=None):
        with pytest.raises(ServiceUnavailableException) as exc:
            await provision_workspace(request, _admin(), _settings(), client, MagicMock(), MagicMock())

    # A workspace without a token cannot authenticate its extension — the
    # provision must fail loudly instead of creating a broken workspace.
    assert "mint" in str(exc.value)
    client.provision_workspace.assert_not_called()


@pytest.mark.asyncio
async def test_provision_failure_rolls_back_token_rotation():
    request = WorkspaceProvisionRequest()
    client = _provisionable_client()
    client.provision_workspace = AsyncMock(side_effect=RuntimeError("boom"))
    mint_result = MintResult(token="ctp_x", new_token_id="new-id", superseded_ids=["old-id"])
    rollback = MagicMock()

    with patch("computor_backend.api.coder._check_workspace_access"), \
         patch("computor_backend.api.coder._enforce_template_quota", AsyncMock()), \
         patch("computor_backend.api.coder.get_user_by_id", return_value=MagicMock(id="u1")), \
         patch("computor_backend.api.coder.mint_workspace_token", return_value=mint_result), \
         patch("computor_backend.api.coder.rollback_workspace_token_rotation", rollback):
        with pytest.raises(InternalServerException):
            await provision_workspace(request, _admin(), _settings(), client, MagicMock(), MagicMock())

    # The workspace never received the new token — the rotation is undone so a
    # running workspace keeps its still-deployed old token.
    rollback.assert_called_once()
    assert rollback.call_args[0][2] is mint_result


@pytest.mark.asyncio
async def test_failed_token_update_build_fails_the_provision():
    """A token-update build that cannot start must raise, not report success —
    the old token was already rotated out, so 'success' would hand back a
    workspace whose extension can no longer authenticate."""
    client = CoderClient(settings=MagicMock())
    user = MagicMock()
    user.username = "u-abc"
    client.get_or_create_user = AsyncMock(return_value=(user, False))
    details = MagicMock()
    details.workspace.template_name = "python-workspace"
    details.workspace.id = "ws1"
    client.get_workspace = AsyncMock(return_value=details)
    client._update_workspace_token = AsyncMock(return_value=False)

    with pytest.raises(CoderWorkspaceActionError):
        await client.provision_workspace(
            user_email="s@example.org",
            username="11111111-2222-3333-4444-555555555555",
            template="python-workspace",
            computor_auth_token="ctp_x",
        )
