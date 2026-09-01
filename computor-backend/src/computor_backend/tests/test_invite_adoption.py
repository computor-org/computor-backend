"""Invite acceptance must adopt pre-provisioned users, not deadlock on them.

computor-org/issues#382: an admin added a user by email, then created an
invite link — acceptance refused with "already registered", the user could
never obtain a login, and nothing in the UI could resolve the state.

``accept_invite`` now adopts an existing user with that email when the row
has never authenticated (no builtin account, no API tokens, no consent):
the Keycloak login is provisioned and the invite's roles land on the
EXISTING user, keeping memberships and profile. A user with real login
evidence still blocks the email, as do banned and archived rows.

Integration tests against the live dev postgres; Keycloak is mocked out.
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

import computor_backend.business_logic.auth as auth_bl
from computor_backend.api.invites import accept_invite
from computor_backend.exceptions import BadRequestException
from computor_backend.model.auth import Account, User
from computor_backend.model.invite import InviteLink
from computor_backend.model.role import UserRole
from computor_types.invites import InviteAccept

from computor_backend.tests.test_user_connect import _Scaffold


@pytest.fixture
def world(session):
    w = _Scaffold(session)
    w.invite_ids = []
    try:
        yield w
    finally:
        session.rollback()
        for invite_id in w.invite_ids:
            session.query(InviteLink).filter(InviteLink.id == invite_id).delete(
                synchronize_session=False
            )
        session.commit()
        w.teardown()


@pytest.fixture
def kc(monkeypatch):
    """Mock Keycloak provisioning — returns (kc_user_id, created)."""
    mock = AsyncMock(return_value=("kc-user-id", True))
    monkeypatch.setattr(auth_bl, "provision_keycloak_login", mock)
    return mock


def _invite(session, world, email=None, roles=None) -> InviteLink:
    invite = InviteLink(
        token=InviteLink.generate_token(),
        email=email,
        max_uses=1,
        use_count=0,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        roles=roles or [],
    )
    session.add(invite)
    session.flush()
    world.invite_ids.append(str(invite.id))
    return invite


def test_pre_provisioned_user_is_adopted(world, session, kc):
    email = f"invitee_{world.sfx}@example.test"
    pre = world.user(email)
    world.member(pre, group=world.group)
    invite = _invite(session, world, email=email, roles=["_user_manager"])
    session.commit()

    result = asyncio.run(
        accept_invite(
            invite.token,
            InviteAccept(
                email=email, password="secret-pass-123",
                given_name="Winfried", family_name="Kern",
            ),
            session,
        )
    )

    assert result["adopted"] is True
    assert result["user_id"] == str(pre.id)
    kc.assert_awaited_once()
    # No duplicate row; names updated; role granted; invite consumed.
    assert session.query(User).filter(User.email == email).count() == 1
    fresh = session.query(User).filter(User.id == str(pre.id)).one()
    assert fresh.given_name == "Winfried"
    assert session.query(UserRole).filter(
        UserRole.user_id == str(pre.id), UserRole.role_id == "_user_manager"
    ).first() is not None
    session.refresh(invite)
    assert invite.use_count == 1
    session.query(UserRole).filter(UserRole.user_id == str(pre.id)).delete(
        synchronize_session=False
    )
    session.commit()


def test_adoption_matches_email_case_insensitively(world, session, kc):
    email = f"Case_{world.sfx}@Example.Test"
    pre = world.user(email)
    invite = _invite(session, world)
    session.commit()

    result = asyncio.run(
        accept_invite(
            invite.token,
            InviteAccept(
                email=email.lower(), password="secret-pass-123",
                given_name="C", family_name="I",
            ),
            session,
        )
    )
    assert result["adopted"] is True
    assert result["user_id"] == str(pre.id)


def test_adoption_skips_roles_already_held(world, session, kc):
    email = f"role_{world.sfx}@example.test"
    pre = world.user(email)
    session.add(UserRole(user_id=pre.id, role_id="_user_manager"))
    invite = _invite(session, world, roles=["_user_manager"])
    session.commit()

    result = asyncio.run(
        accept_invite(
            invite.token,
            InviteAccept(
                email=email, password="secret-pass-123",
                given_name="R", family_name="H",
            ),
            session,
        )
    )
    assert result["adopted"] is True
    assert session.query(UserRole).filter(
        UserRole.user_id == str(pre.id), UserRole.role_id == "_user_manager"
    ).count() == 1
    session.query(UserRole).filter(UserRole.user_id == str(pre.id)).delete(
        synchronize_session=False
    )
    session.commit()


def test_user_with_login_evidence_still_blocks(world, session, kc):
    email = f"active_{world.sfx}@example.test"
    active = world.user(email)
    session.add(
        Account(
            provider="keycloak",
            type="oidc",
            provider_account_id=f"sub-{world.sfx}",
            user_id=active.id,
            builtin=True,
        )
    )
    invite = _invite(session, world)
    session.commit()

    with pytest.raises(BadRequestException) as exc:
        asyncio.run(
            accept_invite(
                invite.token,
                InviteAccept(
                    email=email, password="secret-pass-123",
                    given_name="A", family_name="U",
                ),
                session,
            )
        )
    assert "sign in" in str(exc.value.detail)
    kc.assert_not_awaited()
    session.rollback()
    session.refresh(invite)
    assert invite.use_count == 0


def test_banned_pre_provisioned_user_is_refused(world, session, kc):
    email = f"banned_{world.sfx}@example.test"
    banned = world.user(email)
    banned.banned_at = datetime.now(timezone.utc)
    invite = _invite(session, world)
    session.commit()

    with pytest.raises(BadRequestException):
        asyncio.run(
            accept_invite(
                invite.token,
                InviteAccept(
                    email=email, password="secret-pass-123",
                    given_name="B", family_name="U",
                ),
                session,
            )
        )
    kc.assert_not_awaited()
    session.rollback()


def test_fresh_email_still_creates_a_user(world, session, kc):
    email = f"fresh_{uuid.uuid4().hex[:8]}@example.test"
    invite = _invite(session, world)
    session.commit()

    result = asyncio.run(
        accept_invite(
            invite.token,
            InviteAccept(
                email=email, password="secret-pass-123",
                given_name="F", family_name="N",
            ),
            session,
        )
    )
    assert result["adopted"] is False
    created = session.query(User).filter(User.email == email).one()
    world.user_ids.append(str(created.id))
