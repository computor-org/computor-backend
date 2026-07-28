"""Unit tests for the documents ForwardAuth endpoint (verify_documents_access).

The ``/docs`` static-server has no authentication of its own, so this endpoint is
the only thing standing between the documents tree and anyone who can reach
Traefik. The tests that matter are therefore about the *wiring*: that the route
exists, that it is bound to the real authentication dependency, and that a
successful call grants without leaking anything into the response.
"""

import pytest

from computor_backend.api.auth import auth_router, verify_documents_access
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal


def _route():
    for route in auth_router.routes:
        if getattr(route, "name", None) == "verify_documents_access":
            return route
    raise AssertionError("verify-documents-access route is not registered")


@pytest.mark.asyncio
async def test_authenticated_user_is_granted():
    resp = await verify_documents_access(Principal(user_id="some-user-uuid"))
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_grant_carries_no_body():
    # Traefik returns the auth response to the client on denial and forwards the
    # original request on success — the grant itself must say nothing about the user.
    resp = await verify_documents_access(Principal(user_id="some-user-uuid"))
    assert not resp.body


def test_route_is_registered_on_the_expected_path():
    # The compose ForwardAuth address must match this exactly.
    assert _route().path == "/auth/verify-documents-access"
    assert "GET" in _route().methods


def test_route_requires_authentication():
    # The whole point: no anonymous access. If someone swaps this for an
    # optional-principal dependency, /docs silently goes public again.
    dependency_calls = [d.call for d in _route().dependant.dependencies]
    assert get_current_principal in dependency_calls
