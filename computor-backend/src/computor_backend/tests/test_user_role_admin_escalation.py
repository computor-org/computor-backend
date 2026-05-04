"""Regression tests for the ``POST /user-roles`` privilege-escalation
fix.

Two bugs landed together:

1. ``ReadOnlyPermissionHandler.can_perform_action`` had no ``context``
   keyword arg, but ``business_logic/crud.py::create_entity`` passes
   one. Every POST to a ReadOnly-registered entity 500'd with
   ``TypeError``. Test below: the handler now accepts ``context``.

2. Once that 500 was fixed, a non-admin holding ``_user_manager``
   would have been able to POST ``/user-roles`` with
   ``role_id='_admin'`` and grant themselves (or anyone) the system
   ``_admin`` role. ``UserRole`` is now registered with a dedicated
   ``UserRolePermissionHandler`` that mirrors the
   ``_manager``-can't-promote-to-``_owner`` rule from PR #112: the
   ``user_role:create/update/delete`` claim is necessary but never
   sufficient for the protected ``_admin`` role.

These tests are pure-Python — no DB, no auth machinery — so they
stay fast and independent of the example fixtures.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from computor_backend.permissions.handlers_impl import (
    ReadOnlyPermissionHandler,
    UserRolePermissionHandler,
)
from computor_backend.permissions.principal import Principal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _admin() -> Principal:
    return Principal(user_id="u-admin", is_admin=True)


def _user_manager() -> Principal:
    """A non-admin principal that holds the ``_user_manager`` role.

    The handler treats ``user_role:<action>`` as the gating claim, so
    we model that with a fake claims object whose
    ``has_general_permission`` answers True for the relevant resource.
    Avoids spinning up the full claim-builder pipeline.
    """
    p = Principal(user_id="u-mgr", is_admin=False)
    p.claims = SimpleNamespace(
        has_general_permission=lambda resource, action: resource == "user_role",
        has_dependent_permission=lambda *a, **kw: False,
        dependent={},
    )
    return p


def _outsider() -> Principal:
    """Non-admin with no relevant claims — baseline negative case."""
    p = Principal(user_id="u-out", is_admin=False)
    p.claims = SimpleNamespace(
        has_general_permission=lambda *a, **kw: False,
        has_dependent_permission=lambda *a, **kw: False,
        dependent={},
    )
    return p


@pytest.fixture
def handler():
    """Build the handler against a model-shaped stub.

    ``__tablename__`` drives ``check_general_permission``'s claim name
    lookup (``user_role:<action>``). ``role_id`` is referenced by
    ``build_query`` for the ``!= "_admin"`` filter; SQLAlchemy
    expression objects are not needed since we never execute the query
    here — we only assert it was filtered.
    """
    fake_model = SimpleNamespace(
        __tablename__="user_role",
        __name__="UserRole",
        role_id=SimpleNamespace(__ne__=lambda other: ("role_id != ", other)),
    )
    return UserRolePermissionHandler(fake_model)


# ---------------------------------------------------------------------------
# Bug 1 — ReadOnlyPermissionHandler signature
# ---------------------------------------------------------------------------


class TestReadOnlyHandlerAcceptsContext:
    """The crash that hid the security hole. Caller passes
    ``context=...`` per the base ``PermissionHandler`` signature; if
    the subclass doesn't accept it we get a TypeError → 500."""

    def test_signature_accepts_context_kwarg(self):
        # Build a minimal handler instance; context is ignored for
        # read-only entities but must not raise.
        fake_model = SimpleNamespace(__tablename__="role", __name__="Role")
        h = ReadOnlyPermissionHandler(fake_model)
        # Admin short-circuits — exercising the kwarg, not the body.
        assert h.can_perform_action(
            _admin(), "create", resource_id=None, context={"role_id": "_admin"}
        ) is True


# ---------------------------------------------------------------------------
# Bug 2 — UserRole admin-escalation guard, create path
# ---------------------------------------------------------------------------


class TestCreateAdminEscalationBlocked:
    def test_admin_can_grant_admin(self, handler):
        # Sanity: admins can grant any role, including ``_admin``.
        assert handler.can_perform_action(
            _admin(), "create", context={"role_id": "_admin"}
        ) is True

    def test_user_manager_can_grant_non_admin(self, handler):
        # The legitimate use case: a non-admin user_manager promotes
        # someone to ``_user_manager`` themselves.
        assert handler.can_perform_action(
            _user_manager(), "create", context={"role_id": "_user_manager"}
        ) is True

    def test_user_manager_cannot_grant_admin(self, handler):
        # The vulnerability the report flagged.
        assert handler.can_perform_action(
            _user_manager(), "create", context={"role_id": "_admin"}
        ) is False

    def test_outsider_cannot_grant_anything(self, handler):
        # Regression: a non-admin without the claim still gets nothing.
        assert handler.can_perform_action(
            _outsider(), "create", context={"role_id": "_user_manager"}
        ) is False

    def test_user_manager_create_without_context_allowed(self, handler):
        # Defensive: if a caller forgets to pass context (shouldn't
        # happen via the normal CRUD path), don't false-positive a
        # block. The build_query filter still keeps non-admins away
        # from existing admin rows on update/delete.
        assert handler.can_perform_action(
            _user_manager(), "create", context=None
        ) is True


# ---------------------------------------------------------------------------
# Bug 2 — UserRole admin-escalation guard, read / update / delete paths
# ---------------------------------------------------------------------------


class TestBuildQueryFiltersAdminRows:
    def test_admin_sees_all_rows_on_write(self, handler):
        # Admin gets the unfiltered table back for update/delete.
        db = MagicMock()
        result = handler.build_query(_admin(), "delete", db)
        # Admin path returns ``db.query(self.entity)`` directly;
        # the filter chain is never invoked.
        db.query.return_value.filter.assert_not_called()
        assert result is db.query.return_value

    def test_user_manager_delete_query_excludes_admin(self, handler):
        # Non-admin write paths get a query that filters out admin
        # rows. The endpoint then resolves an admin-targeted URL to
        # NotFound rather than letting the delete succeed silently.
        db = MagicMock()
        handler.build_query(_user_manager(), "delete", db)
        db.query.return_value.filter.assert_called_once()

    def test_user_manager_update_query_excludes_admin(self, handler):
        db = MagicMock()
        handler.build_query(_user_manager(), "update", db)
        db.query.return_value.filter.assert_called_once()

    def test_reads_unfiltered_for_user_manager(self, handler):
        # Reads (list / get) are open by design — needed so a user
        # manager can SEE who is admin even though they can't change it.
        db = MagicMock()
        handler.build_query(_user_manager(), "list", db)
        db.query.return_value.filter.assert_not_called()

    def test_outsider_write_raises_forbidden(self, handler):
        from computor_backend.exceptions import ForbiddenException
        with pytest.raises(ForbiddenException):
            handler.build_query(_outsider(), "delete", MagicMock())
