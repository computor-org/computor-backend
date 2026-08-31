"""Regression tests for the invite-link admin-escalation fix (#403).

``POST /admin/invites`` used to store ``payload.roles`` unvalidated and
``accept_invite`` assigned them straight into ``user_role`` — bypassing
the ``UserRolePermissionHandler`` guard entirely. A non-admin
``_user_manager`` could mint an invite carrying ``_admin`` and collect
the role through a throwaway acceptance.

The fix has two layers:

1. ``create_invite`` rejects admin-conferring roles for non-admin
   creators (403 / AUTHZ_005) and unknown role ids (400).
2. ``accept_invite`` re-checks the creator's CURRENT roles before
   granting an admin-conferring role, so invites predating the guard
   (or whose creator lost admin since) are defused.

Alongside: ``delete_user_role`` now names the denial (403 / AUTHZ_005)
instead of hiding admin rows behind a "UserRole not found" 404 — the
misleading error that produced issue #403's bug report.

Pure-Python with mocked DB sessions — no fixtures, no network.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from computor_backend.api.invites import create_invite, _creator_is_admin
from computor_backend.business_logic.user_roles import delete_user_role
from computor_backend.exceptions import BadRequestException, ForbiddenException
from computor_backend.model.role import UserRole
from computor_backend.permissions.principal import Principal
from computor_backend.permissions.roles import grants_system_admin
from computor_types.invites import InviteLinkCreate


def _user_manager() -> Principal:
    return Principal(user_id="u-mgr", is_admin=False)


def _db_for_create(known_role_rows):
    """Mock Session for ``create_invite``.

    Two queries run before any invite is built: the ``UserRole`` lookup
    inside ``_require_invite_manager`` (must find a ``_user_manager``
    row so the caller passes the gate) and the ``Role.id`` existence
    check (returns ``known_role_rows``).
    """
    db = MagicMock()

    def query_side_effect(arg):
        m = MagicMock()
        if arg is UserRole:
            m.filter.return_value.first.return_value = object()
        else:
            m.filter.return_value = known_role_rows
        return m

    db.query.side_effect = query_side_effect
    return db


class TestGrantsSystemAdminPredicate:
    def test_builtin_admin(self):
        assert grants_system_admin("_admin") is True

    def test_custom_admin_suffix(self):
        # Principal.set_is_admin_from_roles flags any ``*_admin`` role,
        # so the guard predicate must too.
        assert grants_system_admin("billing_admin") is True

    def test_non_admin_roles(self):
        assert grants_system_admin("_user_manager") is False
        assert grants_system_admin("_administrator") is False


class TestCreateInviteEscalationBlocked:
    def test_user_manager_cannot_mint_admin_invite(self):
        db = _db_for_create(known_role_rows=[("_admin",)])
        payload = InviteLinkCreate(roles=["_admin"])
        with pytest.raises(ForbiddenException) as exc:
            asyncio.run(create_invite(payload, _user_manager(), db))
        assert exc.value.status_code == 403
        db.add.assert_not_called()

    def test_user_manager_cannot_smuggle_admin_among_others(self):
        db = _db_for_create(known_role_rows=[("_admin",), ("_user_manager",)])
        payload = InviteLinkCreate(roles=["_user_manager", "_admin"])
        with pytest.raises(ForbiddenException):
            asyncio.run(create_invite(payload, _user_manager(), db))
        db.add.assert_not_called()

    def test_unknown_role_rejected(self):
        db = _db_for_create(known_role_rows=[])
        payload = InviteLinkCreate(roles=["_no_such_role"])
        with pytest.raises(BadRequestException):
            asyncio.run(create_invite(payload, _user_manager(), db))
        db.add.assert_not_called()


class TestAcceptTimeCreatorRecheck:
    def test_creator_with_admin_role_passes(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = [("_admin",)]
        invite = SimpleNamespace(created_by="u-boss")
        assert _creator_is_admin(invite, db) is True

    def test_creator_without_admin_role_fails(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = [("_user_manager",)]
        invite = SimpleNamespace(created_by="u-mgr")
        assert _creator_is_admin(invite, db) is False

    def test_missing_creator_fails_closed(self):
        assert _creator_is_admin(SimpleNamespace(created_by=None), MagicMock()) is False


class TestDeleteUserRoleNamesTheDenial:
    def test_non_admin_removing_admin_role_gets_descriptive_403(self):
        db = MagicMock()
        with pytest.raises(ForbiddenException) as exc:
            delete_user_role("u-target", "_admin", _user_manager(), db)
        assert exc.value.status_code == 403
        # Raised before any DB interaction.
        db.query.assert_not_called()
