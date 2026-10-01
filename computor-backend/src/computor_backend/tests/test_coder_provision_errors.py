"""Regression tests for error handling in the Coder workspace-provision endpoint.

Production hit `NameError: name 'HTTPException' is not defined` from the endpoint's
`except HTTPException:` clause (HTTPException was never imported), which masked the
real 503 ("template not yet available"). The clause now catches ComputorException —
typed exceptions propagate untouched; unexpected ones are mapped by _handle_coder_error.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from types import SimpleNamespace
from uuid import UUID

import pytest

from computor_backend.api import coder as coder_api
from computor_backend.api.coder import provision_workspace
from computor_backend.coder.exceptions import (
    CoderUserNotFoundError,
    CoderTemplateNotFoundError,
    CoderConnectionError,
)
from computor_backend.exceptions import ServiceUnavailableException
from computor_backend.permissions.principal import Claims, Principal
from computor_types.workspace_roles import WorkspaceProvisionRequest
from computor_backend.coder.naming import encode_coder_username


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


@pytest.mark.asyncio
async def test_public_provision_reaches_reservation_and_coder(monkeypatch):
    """A signed-in learner's provision request reaches the admission boundary."""
    user_id = UUID("bf2b67d1-7596-4af9-a570-3e84a1456bb3")
    user = SimpleNamespace(id=user_id)
    principal = Principal(
        user_id=str(user_id),
        claims=Claims(general={"workspace": {"provision_self"}}),
    )
    client = MagicMock()
    client.get_template_id = AsyncMock(return_value="template-id")
    client._find_user_by_email = AsyncMock(side_effect=CoderUserNotFoundError("learner@example.test"))
    result = SimpleNamespace(workspace=SimpleNamespace(name="vscode"))
    client.provision_workspace = AsyncMock(return_value=result)
    reservation = AsyncMock()
    monkeypatch.setattr(coder_api, "_require_verified_workspace_limits", AsyncMock())
    monkeypatch.setenv("COMPUTOR_PUBLIC_DEPLOYMENT", "true")
    monkeypatch.setattr(coder_api, "is_template_enabled", lambda *_: True)
    monkeypatch.setattr(coder_api, "_enforce_workspace_admission", AsyncMock())
    monkeypatch.setattr(coder_api, "reserve_public_container", reservation)
    monkeypatch.setattr(coder_api, "get_user_by_id", lambda *_: user)
    monkeypatch.setattr(coder_api, "get_user_email", lambda *_: "learner@example.test")
    monkeypatch.setattr(coder_api, "get_user_fullname", lambda *_: "Synthetic Learner")
    monkeypatch.setattr(coder_api, "mint_workspace_token", lambda *_a, **_k: "synthetic-token")
    monkeypatch.setattr(coder_api, "member_template_policy", lambda *_: (None, None))
    monkeypatch.setattr(coder_api, "current_workspace_app_credentials", lambda *_: (None, None))

    response = await provision_workspace(
        WorkspaceProvisionRequest(template="vscode-workspace"), principal,
        _settings(), client, MagicMock(), MagicMock(),
    )

    assert response is result
    reservation.assert_awaited_once_with(client, encode_coder_username(str(user_id)), "vscode")
    client.provision_workspace.assert_awaited_once()
