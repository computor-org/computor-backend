"""A token minter may not grant scopes beyond the target service type's defaults.

Token scopes become ordinary ``("permissions", scope)`` claims that non-admin
permission handlers honour. Without a ceiling, a ``_service_manager`` — whose
own claims are only ``service:*`` and ``api_token:*`` — could mint a service
token carrying ``result:update`` or ``user:create``, authenticate as that
service, and forge grades in any course. These tests pin the ceiling.
"""
from types import SimpleNamespace

import pytest

from computor_backend.business_logic.api_tokens import (
    DEFAULT_SERVICE_SCOPES,
    assert_may_grant_scopes,
)
from computor_backend.exceptions import ForbiddenException


class _Principal(SimpleNamespace):
    """Minimal stand-in for permissions.Principal."""


def _service_manager():
    return _Principal(is_admin=False, user_id="mgr-1")


def _admin():
    return _Principal(is_admin=True, user_id="admin-1")


@pytest.fixture
def testing_service(monkeypatch):
    """A service whose type category is 'testing'."""
    monkeypatch.setattr(
        "computor_backend.business_logic.api_tokens.get_default_scopes_for_service",
        lambda *a, **k: list(DEFAULT_SERVICE_SCOPES["testing"]),
    )
    return SimpleNamespace(id="svc-user-1", is_service=True)


@pytest.fixture
def agent_service(monkeypatch):
    """An 'agent' service — no default scopes at all."""
    monkeypatch.setattr(
        "computor_backend.business_logic.api_tokens.get_default_scopes_for_service",
        lambda *a, **k: [],
    )
    return SimpleNamespace(id="svc-user-2", is_service=True)


def test_service_manager_may_grant_the_types_own_scopes(testing_service):
    """The intended workflow must keep working: provision a testing worker."""
    assert_may_grant_scopes(
        testing_service,
        ["result:create", "result:update", "example:download"],
        _service_manager(),
        db=None,
    )


def test_service_manager_cannot_grant_user_create(testing_service):
    with pytest.raises(ForbiddenException) as exc:
        assert_may_grant_scopes(
            testing_service,
            ["result:create", "user:create"],
            _service_manager(),
            db=None,
        )
    assert "user:create" in str(exc.value.detail)


def test_service_manager_cannot_grant_result_write_to_an_agent(agent_service):
    """An agent type has no defaults, so nothing may be granted by a non-admin."""
    with pytest.raises(ForbiddenException) as exc:
        assert_may_grant_scopes(
            agent_service, ["result:update"], _service_manager(), db=None
        )
    assert "result:update" in str(exc.value.detail)


def test_admin_may_grant_anything(agent_service):
    assert_may_grant_scopes(
        agent_service, ["user:create", "result:update"], _admin(), db=None
    )


def test_empty_scopes_are_always_allowed(agent_service):
    """Empty means 'fill in the type defaults', which is not an escalation."""
    assert_may_grant_scopes(agent_service, [], _service_manager(), db=None)
    assert_may_grant_scopes(agent_service, None, _service_manager(), db=None)


def test_every_default_scope_set_is_grantable_by_a_service_manager(monkeypatch):
    """No category may define a default its own manager would be refused."""
    for category, scopes in DEFAULT_SERVICE_SCOPES.items():
        monkeypatch.setattr(
            "computor_backend.business_logic.api_tokens.get_default_scopes_for_service",
            lambda *a, _s=scopes, **k: list(_s),
        )
        assert_may_grant_scopes(
            SimpleNamespace(id=f"svc-{category}"), list(scopes), _service_manager(), db=None
        )
