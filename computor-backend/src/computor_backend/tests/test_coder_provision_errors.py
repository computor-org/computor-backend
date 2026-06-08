"""Regression tests for error handling in the Coder workspace-provision endpoint.

Production hit `NameError: name 'HTTPException' is not defined` from the endpoint's
`except HTTPException:` clause (HTTPException was never imported), which masked the
real 503 ("template not yet available"). The clause now catches ComputorException —
typed exceptions propagate untouched; unexpected ones are mapped by _handle_coder_error.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from computor_backend.api.coder import provision_workspace
from computor_backend.coder.exceptions import (
    CoderTemplateNotFoundError,
    CoderConnectionError,
)
from computor_backend.exceptions import ServiceUnavailableException
from computor_backend.permissions.principal import Principal
from computor_types.workspace_roles import WorkspaceProvisionRequest


def _admin():
    return Principal(user_id="u1", roles=["_admin"])


@pytest.mark.asyncio
async def test_template_not_found_propagates_as_service_unavailable():
    request = WorkspaceProvisionRequest()  # default template = python-workspace
    client = MagicMock()
    client.get_template_id = AsyncMock(side_effect=CoderTemplateNotFoundError("python-workspace"))

    with patch("computor_backend.api.coder._check_workspace_access"):
        with pytest.raises(ServiceUnavailableException) as exc:
            await provision_workspace(request, _admin(), MagicMock(), client, MagicMock(), MagicMock())

    # The typed 503 (not a NameError, not a generic 500) reaches the caller intact.
    assert "not yet available" in str(exc.value)


@pytest.mark.asyncio
async def test_unexpected_coder_error_is_mapped_not_nameerror():
    request = WorkspaceProvisionRequest()
    client = MagicMock()
    client.get_template_id = AsyncMock(side_effect=CoderConnectionError("down"))

    with patch("computor_backend.api.coder._check_workspace_access"):
        with pytest.raises(ServiceUnavailableException) as exc:
            await provision_workspace(request, _admin(), MagicMock(), client, MagicMock(), MagicMock())

    # Mapped by _handle_coder_error (the `except Exception` path), not a NameError.
    assert "connect to Coder" in str(exc.value)
