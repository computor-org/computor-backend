"""A user may edit their own name — and only their own name.

Saving the web profile page patches the user row before the profile row, so
until this carve-out existed every non-privileged user got
``403 Insufficient permissions to update user`` and lost their profile edits
along with it (computor-org/issues#334).

The carve-out is deliberately narrow: ``email`` is the join key between the
Computor user, the Keycloak identity and the git-server handle, and
``properties`` carries provisioning state. Both stay admin/_user_manager only.
"""
from unittest.mock import MagicMock

import pytest

from computor_backend.exceptions import ForbiddenException
from computor_backend.interfaces.user import custom_permissions_user
from computor_backend.model.auth import User
from computor_backend.permissions.handlers_impl import UserPermissionHandler
from computor_backend.permissions.principal import Principal, build_claims
from computor_backend.permissions.role_setup import claims_user_manager
from computor_types.users import UserUpdate


def make_db():
    db = MagicMock()
    q = MagicMock()
    q.filter.return_value = q
    db.query.return_value = q
    return db


def _self() -> Principal:
    return Principal(user_id='u1', roles=['user'])


def _user_manager() -> Principal:
    return Principal(
        user_id='um',
        roles=['_user_manager'],
        claims=build_claims(claims_user_manager()),
    )


class TestSelfUpdateHandler:
    def test_own_row_is_updatable(self):
        handler = UserPermissionHandler(User)
        assert handler.can_perform_action(_self(), 'update', resource_id='u1') is True

    def test_someone_elses_row_is_not(self):
        handler = UserPermissionHandler(User)
        assert handler.can_perform_action(_self(), 'update', resource_id='u2') is False

    def test_update_query_is_scoped_to_the_principal(self):
        """Not a bare ``db.query(User)`` — a patch aimed elsewhere must 404."""
        db = make_db()
        handler = UserPermissionHandler(User)
        handler.build_query(_self(), 'update', db)
        db.query.return_value.filter.assert_called_once()

    def test_delete_is_still_refused(self):
        db = make_db()
        handler = UserPermissionHandler(User)
        with pytest.raises(ForbiddenException):
            handler.build_query(_self(), 'delete', db)


class TestSelfUpdateFieldWhitelist:
    def test_name_change_passes(self):
        db = make_db()
        custom_permissions_user(_self(), db, 'u1', UserUpdate(given_name='Ada'))

    @pytest.mark.parametrize(
        'payload',
        [
            UserUpdate(email='someone.else@example.org'),
            UserUpdate(properties={'gitlab': {'token': 'x'}}),
            UserUpdate(given_name='Ada', email='someone.else@example.org'),
        ],
    )
    def test_managed_fields_are_refused(self, payload):
        db = make_db()
        with pytest.raises(ForbiddenException):
            custom_permissions_user(_self(), db, 'u1', payload)

    def test_user_manager_keeps_the_full_surface(self):
        db = make_db()
        custom_permissions_user(
            _user_manager(), db, 'u1', UserUpdate(email='new@example.org')
        )

    def test_admin_keeps_the_full_surface(self):
        db = make_db()
        admin = Principal(user_id='a', is_admin=True, roles=['_admin'])
        custom_permissions_user(admin, db, 'u1', UserUpdate(email='new@example.org'))
