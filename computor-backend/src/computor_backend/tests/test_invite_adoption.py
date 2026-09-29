"""Invite acceptance must adopt pre-provisioned users, not deadlock on them.

computor-org/issues#382: an admin added a user by email, then created an
invite link — acceptance refused with "already registered", the user could
never obtain a login, and nothing in the UI could resolve the state.

``accept_invite`` adopts an existing user with that email only when the
invite was issued for exactly that address and the row has never
authenticated (no builtin account, no API tokens, no consent) and holds no
staff role: the Keycloak login is provisioned UNVERIFIED (VERIFY_EMAIL), the
row itself is left untouched, and the invite's roles land on the EXISTING
user. A generic invite never adopts (that was an account takeover), and a
user with real login evidence still blocks the email, as do banned and
archived rows.

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
    # Ownership is proven by Keycloak's email verification, not the invite.
    assert kc.await_args.kwargs["email_verified"] is False
    # No duplicate row; row untouched until verified; role granted; consumed.
    assert session.query(User).filter(User.email == email).count() == 1
    fresh = session.query(User).filter(User.id == str(pre.id)).one()
    assert fresh.given_name != "Winfried"
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
    invite = _invite(session, world, email=email)
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
    session.add(UserRole(user_id=pre.id, role_id="_workspace_user"))
    invite = _invite(session, world, email=email, roles=["_workspace_user"])
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
        UserRole.user_id == str(pre.id), UserRole.role_id == "_workspace_user"
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
    invite = _invite(session, world, email=email)
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
    invite = _invite(session, world, email=email)
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


def _accept(invite, email, session):
    return asyncio.run(
        accept_invite(
            invite.token,
            InviteAccept(email=email, password="attacker-pass-123",
                         given_name="Mallory", family_name="X"),
            session,
        )
    )


def test_generic_invite_cannot_take_over_a_pre_created_admin(world, session, kc):
    """Reviewer repro: an unrestricted seed invite + the victim's email adopted
    a never-signed-in ADMIN row and reset its Keycloak password."""
    email = f"victim_admin_{world.sfx}@example.test"
    victim = world.user(email)
    session.add(UserRole(user_id=victim.id, role_id="_admin"))
    invite = _invite(session, world)
    session.commit()

    with pytest.raises(BadRequestException):
        _accept(invite, email, session)
    kc.assert_not_awaited()
    session.rollback()
    session.refresh(invite)
    assert invite.use_count == 0
    session.query(UserRole).filter(UserRole.user_id == str(victim.id)).delete(
        synchronize_session=False
    )
    session.commit()


def test_even_a_bound_invite_never_adopts_a_staff_row(world, session, kc):
    email = f"staff_{world.sfx}@example.test"
    staff = world.user(email)
    session.add(UserRole(user_id=staff.id, role_id="_admin"))
    invite = _invite(session, world, email=email)
    session.commit()

    with pytest.raises(BadRequestException):
        _accept(invite, email, session)
    kc.assert_not_awaited()
    session.rollback()
    session.query(UserRole).filter(UserRole.user_id == str(staff.id)).delete(
        synchronize_session=False
    )
    session.commit()


def test_generic_invite_cannot_adopt_an_unused_non_staff_row(world, session, kc):
    email = f"plain_{world.sfx}@example.test"
    world.user(email)
    invite = _invite(session, world)
    session.commit()

    with pytest.raises(BadRequestException):
        _accept(invite, email, session)
    kc.assert_not_awaited()
    session.rollback()


def test_existing_keycloak_login_is_never_reset(world, session, monkeypatch):
    """provision_keycloak_login refuses instead of resetting the password."""
    from computor_backend.exceptions import ConflictException

    calls = []

    class _KC:
        async def _get_user_id_by_email(self, email):
            return "existing-kc-user"

        async def set_user_password(self, *args, **kwargs):  # pragma: no cover
            calls.append(args)

    monkeypatch.setattr(auth_bl, "KeycloakAdminClient", _KC)
    email = f"kcexists_{uuid.uuid4().hex[:8]}@example.test"
    invite = _invite(session, world)
    session.commit()

    with pytest.raises(ConflictException):
        _accept(invite, email, session)
    assert calls == []
    session.rollback()
    session.refresh(invite)
    assert invite.use_count == 0
    assert session.query(User).filter(User.email == email).count() == 0
