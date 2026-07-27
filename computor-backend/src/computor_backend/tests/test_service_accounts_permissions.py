"""Unit tests for service-account and API-token authorization.

Two things are being pinned down here, both security-relevant:

1. ``ApiTokenPermissionHandler`` NARROWS rather than raises (every user owns
   tokens), so a successful ``check_permissions`` is not on its own an
   authorization decision. Callers must filter through the returned query.
   If someone later "simplifies" a call site back to a repository lookup by
   id, the token endpoints silently become readable/revokable by anyone.

2. Token scopes are ADDITIVE — a token on a human account carries that
   account's full role set regardless of the scopes requested. So minting a
   token for someone else is admin-only, and a ``_service_manager`` is
   confined to service accounts.
"""
from types import SimpleNamespace

import pytest

from computor_backend.business_logic.api_tokens import assert_may_mint_token_for
from computor_backend.exceptions import ForbiddenException
from computor_backend.model.service import ApiToken, Service
from computor_backend.permissions.handlers_service import (
    ApiTokenPermissionHandler,
    ServicePermissionHandler,
)


# --------------------------------------------------------------------------
# Fakes: just enough surface for build_query to be exercised without a DB.
# --------------------------------------------------------------------------

class _FakeQuery:
    """Records the filter/join calls so tests can assert on narrowing."""

    def __init__(self, entity):
        self.entity = entity
        self.filters = []
        self.joined = False

    def join(self, *a, **k):
        self.joined = True
        return self

    def filter(self, *a, **k):
        self.filters.append(a)
        return self


class _FakeDB:
    def __init__(self):
        self.queried = None

    def query(self, entity):
        self.queried = entity
        return _FakeQuery(entity)


def _principal(*, is_admin=False, is_service=False, claims=()):
    """A Principal stand-in. ``claims`` are "<resource>:<action>" strings."""
    granted = set(claims)
    return SimpleNamespace(
        user_id="u-caller",
        is_admin=is_admin,
        is_service=is_service,
        permitted=lambda resource, action, *a, **k: (
            is_admin or f"{resource}:{action}" in granted
        ),
    )


SERVICE_MANAGER_CLAIMS = (
    "service:get", "service:list", "service:create",
    "service:update", "service:delete",
    "api_token:get", "api_token:list", "api_token:create",
    "api_token:update", "api_token:delete",
)


# --------------------------------------------------------------------------
# ServicePermissionHandler
# --------------------------------------------------------------------------

def test_service_admin_sees_everything():
    handler = ServicePermissionHandler(Service)
    db = _FakeDB()
    q = handler.build_query(_principal(is_admin=True), "list", db)
    assert db.queried is Service
    assert q.filters == []


def test_service_manager_sees_everything():
    handler = ServicePermissionHandler(Service)
    q = handler.build_query(
        _principal(claims=SERVICE_MANAGER_CLAIMS), "list", _FakeDB()
    )
    assert q.filters == []


@pytest.mark.parametrize("action", ["list", "get", "update", "delete", "create"])
def test_service_plain_user_is_refused(action):
    """No claim, not a service: 403 rather than a silently empty list."""
    handler = ServicePermissionHandler(Service)
    with pytest.raises(ForbiddenException):
        handler.build_query(_principal(), action, _FakeDB())


def test_service_account_may_read_its_own_row():
    """Workers resolve GET /service-accounts/me through this path."""
    handler = ServicePermissionHandler(Service)
    q = handler.build_query(_principal(is_service=True), "get", _FakeDB())
    assert len(q.filters) == 1


def test_service_manager_cannot_write_via_read_claim_only():
    handler = ServicePermissionHandler(Service)
    with pytest.raises(ForbiddenException):
        handler.build_query(_principal(claims=("service:get",)), "delete", _FakeDB())


def test_read_action_maps_onto_the_get_claim():
    """`ACTIONS` has no "read", so no `service:read` claim is ever seeded.

    Legacy call sites passing "read" must still resolve against `service:get`
    instead of falling through to a 403.
    """
    handler = ServicePermissionHandler(Service)
    q = handler.build_query(_principal(claims=("service:get",)), "read", _FakeDB())
    assert q.filters == []


# --------------------------------------------------------------------------
# ApiTokenPermissionHandler
# --------------------------------------------------------------------------

def test_token_admin_is_unfiltered():
    handler = ApiTokenPermissionHandler(ApiToken)
    q = handler.build_query(_principal(is_admin=True), "list", _FakeDB())
    assert q.filters == []
    assert not q.joined


def test_token_service_manager_is_narrowed_to_service_owners():
    """The claim must not widen visibility to every user's tokens."""
    handler = ApiTokenPermissionHandler(ApiToken)
    q = handler.build_query(
        _principal(claims=SERVICE_MANAGER_CLAIMS), "list", _FakeDB()
    )
    assert q.joined, "must join User to restrict to is_service owners"
    assert len(q.filters) == 1


def test_token_plain_user_is_narrowed_to_self_and_never_raises():
    """Everyone owns tokens, so this branch narrows instead of 403-ing.

    This is exactly why the business logic must fetch through the returned
    query — see the module docstring.
    """
    handler = ApiTokenPermissionHandler(ApiToken)
    q = handler.build_query(_principal(), "delete", _FakeDB())
    assert not q.joined
    assert len(q.filters) == 1


# --------------------------------------------------------------------------
# The mint guard — the escalation vector
# --------------------------------------------------------------------------

def _user(uid, *, is_service=False):
    return SimpleNamespace(id=uid, is_service=is_service, email=f"{uid}@x")


def test_anyone_may_mint_their_own_token():
    assert_may_mint_token_for(_user("u-caller"), _principal())


def test_admin_may_mint_for_anyone():
    assert_may_mint_token_for(_user("someone"), _principal(is_admin=True))


def test_service_manager_may_mint_for_a_service_account():
    assert_may_mint_token_for(
        _user("svc", is_service=True), _principal(claims=SERVICE_MANAGER_CLAIMS)
    )


def test_service_manager_may_not_mint_for_a_human():
    """The escalation: scopes are additive, so this token would carry that
    human's whole role set — including _admin."""
    with pytest.raises(ForbiddenException):
        assert_may_mint_token_for(
            _user("a-human"), _principal(claims=SERVICE_MANAGER_CLAIMS)
        )


def test_plain_user_may_not_mint_for_a_service_account():
    """check_permissions no longer raises for tokens, so this guard is the
    only thing standing between a plain user and a worker's credentials."""
    with pytest.raises(ForbiddenException):
        assert_may_mint_token_for(_user("svc", is_service=True), _principal())
