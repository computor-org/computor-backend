"""Two-step user deletion policy (computor-org/issues#382).

``guard_user_delete`` (a ``pre_delete`` guard on the User CrudRouter) allows
direct deletion only for pre-provisioned rows that never authenticated. A
user with login evidence must be archived first and may then only be deleted
by a full admin. Self-deletion, admin-role holders, service accounts and
users carrying graded work are always refused.

Integration tests against the live dev postgres.
"""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from computor_backend.business_logic.user_lifecycle import (
    guard_user_delete,
    login_evidence,
)
from computor_backend.exceptions import ConflictException, ForbiddenException
from computor_backend.model.auth import Account
from computor_backend.model.result import Result
from computor_backend.model.role import UserRole
from computor_backend.permissions.principal import Principal

from computor_backend.tests.test_user_connect import _Scaffold


@pytest.fixture
def world(session):
    w = _Scaffold(session)
    try:
        yield w
    finally:
        w.teardown()


def _admin() -> Principal:
    return Principal(user_id="00000000-0000-0000-0000-00000000adad", is_admin=True)


def _manager() -> Principal:
    return Principal(user_id="00000000-0000-0000-0000-0000000000a1", is_admin=False)


def _entity(user, archived=False):
    return SimpleNamespace(
        id=str(user.id),
        is_service=False,
        archived_at=datetime.now(timezone.utc) if archived else None,
    )


def _login(session, world, user):
    session.add(
        Account(
            provider="keycloak",
            type="oidc",
            provider_account_id=f"sub-{world.sfx}-{str(user.id)[:8]}",
            user_id=user.id,
            builtin=True,
        )
    )
    session.flush()


def test_never_logged_in_user_passes(world, session):
    user = world.user(f"stuck_{world.sfx}@example.test")
    world.member(user, group=world.group)
    session.commit()
    assert login_evidence(str(user.id), session) is None
    guard_user_delete(_entity(user), _manager(), session)  # must not raise


def test_self_delete_is_refused(world, session):
    user = world.user(f"self_{world.sfx}@example.test")
    session.commit()
    me = Principal(user_id=str(user.id), is_admin=True)
    with pytest.raises(ForbiddenException):
        guard_user_delete(_entity(user), me, session)


def test_service_account_is_refused(world, session):
    user = world.user(f"svc_{world.sfx}@example.test")
    session.commit()
    entity = _entity(user)
    entity.is_service = True
    with pytest.raises(ConflictException):
        guard_user_delete(entity, _admin(), session)


def test_admin_role_holder_is_refused(world, session):
    user = world.user(f"boss_{world.sfx}@example.test")
    session.add(UserRole(user_id=user.id, role_id="_admin"))
    session.commit()
    with pytest.raises(ForbiddenException):
        guard_user_delete(_entity(user), _admin(), session)
    session.query(UserRole).filter(UserRole.user_id == str(user.id)).delete(
        synchronize_session=False
    )
    session.commit()


def test_logged_in_unarchived_is_refused_even_for_admin(world, session):
    user = world.user(f"active_{world.sfx}@example.test")
    _login(session, world, user)
    session.commit()
    with pytest.raises(ConflictException) as exc:
        guard_user_delete(_entity(user), _admin(), session)
    assert "Archive" in str(exc.value.detail)


def test_logged_in_archived_needs_full_admin(world, session):
    user = world.user(f"archived_{world.sfx}@example.test")
    _login(session, world, user)
    session.commit()
    with pytest.raises(ForbiddenException):
        guard_user_delete(_entity(user, archived=True), _manager(), session)
    guard_user_delete(_entity(user, archived=True), _admin(), session)  # must not raise


def test_graded_work_always_blocks(world, session):
    user = world.user(f"graded_{world.sfx}@example.test")
    cm = world.member(user, group=world.group)
    content = world.content()
    session.add(
        Result(
            course_member_id=cm.id,
            course_content_id=content.id,
            course_content_type_id=content.course_content_type_id,
            version_identifier=f"v_{world.sfx}",
            status=0,
        )
    )
    session.commit()
    with pytest.raises(ConflictException) as exc:
        guard_user_delete(_entity(user, archived=True), _admin(), session)
    assert "graded" in str(exc.value.detail)
