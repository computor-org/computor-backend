"""
Invite link API endpoints.

Admins and _user_manager role holders can create invite links.
Invite acceptance is public (no authentication required).
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from computor_backend.database import get_db
from computor_backend.business_logic.registration_admission import (
    check_registration_capacity,
    count_registered_users,
    invite_public_status,
    record_invite,
)
from computor_backend.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
    RateLimitException,
)
from computor_backend.model.instance import InstanceSettings
from computor_backend.model.auth import User
from computor_backend.model.invite import InviteLink
from computor_backend.model.role import Role, UserRole
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.permissions.roles import grants_system_admin
from computor_backend.redis_cache import get_redis_client
from computor_backend.utils.client_info import trusted_client_ip
from computor_types.invites import (
    InviteAccept,
    InviteLinkCreate,
    InviteLinkGet,
    InviteLinkList,
    InviteLinkPublic,
    InviteStatusPublic,
)

logger = logging.getLogger(__name__)

invites_router = APIRouter()


def _require_invite_manager(principal: Principal, db: Session) -> None:
    """Raise ForbiddenException unless caller is admin or has _user_manager role."""
    if principal.is_admin:
        return
    user_role = db.query(UserRole).filter(
        UserRole.user_id == principal.user_id,
        UserRole.role_id == "_user_manager",
    ).first()
    if not user_role:
        raise ForbiddenException(detail="Requires _admin or _user_manager role")


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------

@invites_router.post("/admin/invites", response_model=InviteLinkGet, status_code=201)
async def create_invite(
    payload: InviteLinkCreate,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
) -> InviteLinkGet:
    """Create a new invite link (admin or _user_manager)."""
    _require_invite_manager(principal, db)

    requested_roles = payload.roles or []
    if requested_roles:
        # Unknown role ids would only surface as an FK error when the
        # invite is accepted — reject them up front instead.
        known = {row[0] for row in db.query(Role.id).filter(Role.id.in_(requested_roles))}
        unknown = [r for r in requested_roles if r not in known]
        if unknown:
            raise BadRequestException(
                detail=f"Unknown role(s): {', '.join(sorted(unknown))}",
            )

        # Acceptance assigns the invite's roles directly, bypassing the
        # UserRolePermissionHandler escalation guard — so the same rule
        # must hold here: only admins may hand out admin roles.
        if not principal.is_admin and any(grants_system_admin(r) for r in requested_roles):
            raise ForbiddenException(
                error_code="AUTHZ_005",
                detail="Only administrators can create invites that grant the admin role",
                context={"roles": requested_roles},
            )

    expires_at = datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days)

    invite = InviteLink(
        token=InviteLink.generate_token(),
        created_by=principal.user_id,
        email=payload.email.lower().strip() if payload.email else None,
        max_uses=payload.max_uses,
        use_count=0,
        expires_at=expires_at,
        roles=payload.roles,
        note=payload.note,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    logger.info(f"Invite {invite.id} created by {principal.user_id}")
    return _to_get(invite)


@invites_router.get("/admin/invites", response_model=List[InviteLinkList])
async def list_invites(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
) -> List[InviteLinkList]:
    """List all invite links (admin or _user_manager)."""
    _require_invite_manager(principal, db)
    invites = db.query(InviteLink).order_by(InviteLink.created_at.desc()).all()
    return [_to_list(i) for i in invites]


@invites_router.get("/admin/invites/{invite_id}", response_model=InviteLinkGet)
async def get_invite(
    invite_id: str,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
) -> InviteLinkGet:
    """Get a single invite link (admin or _user_manager)."""
    _require_invite_manager(principal, db)
    invite = db.query(InviteLink).filter(InviteLink.id == invite_id).first()
    if not invite:
        raise NotFoundException(detail="Invite not found")
    return _to_get(invite)


@invites_router.delete("/admin/invites/{invite_id}", status_code=204)
async def revoke_invite(
    invite_id: str,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
) -> None:
    """Revoke an invite link (admin or _user_manager)."""
    # In the threadpool: the UPDATE may wait on the invite row lock of a
    # concurrent acceptance, which must not block the event loop.
    def _revoke():
        try:
            _require_invite_manager(principal, db)
            invite = db.query(InviteLink).filter(InviteLink.id == invite_id).first()
            if not invite:
                raise NotFoundException(detail="Invite not found")
            invite.revoked_at = datetime.now(timezone.utc)
            db.commit()
        except BaseException:
            db.rollback()
            raise

    await run_in_threadpool(_revoke)
    logger.info(f"Invite {invite_id} revoked by {principal.user_id}")


# ---------------------------------------------------------------------------
# Public endpoints (no authentication required)
# ---------------------------------------------------------------------------

# Per client IP, fixed windows, on every public invite endpoint. Codes are
# 256-bit random, so this bounds load and abuse, not secrecy. The IP comes
# from trusted_client_ip, which ignores client-supplied forwarding headers.
INVITE_LOOKUP_LIMIT = 30
INVITE_ACCEPT_LIMIT = 10
INVITE_WINDOW = 600


async def _throttle_public_invite(request: Optional[Request], cache, bucket: str, limit: int) -> None:
    """Raise RateLimitException once this client spent ``limit`` in the window.

    Fails open on Redis errors, like the other limiters. Skipped when called
    outside a request (direct calls in tests).
    """
    if request is None:
        return
    key = f"rate_limit:{bucket}:{trusted_client_ip(request)}"
    try:
        count = await cache.incr(key)
        if count == 1:
            await cache.expire(key, INVITE_WINDOW)
    except Exception as e:
        logger.error(f"Invite rate limit check failed: {e}")
        return
    if count > limit:
        raise RateLimitException(
            error_code="RATE_001",
            detail="Too many invite requests. Please wait before trying again.",
            retry_after=INVITE_WINDOW,
        )


@invites_router.get("/invites/{token}/status", response_model=InviteStatusPublic)
async def get_invite_status(
    token: str,
    request: Request,
    db: Session = Depends(get_db),
    cache=Depends(get_redis_client),
) -> InviteStatusPublic:
    """Whether a /join code can still be used (public, no auth, rate-limited).

    Reveals only valid/used/expired/invalid plus whether registration is open
    at all — never who issued the code, its email restriction or its roles.
    """
    await _throttle_public_invite(request, cache, "invite_lookup", INVITE_LOOKUP_LIMIT)
    invite = db.query(InviteLink).filter(InviteLink.token == token[:128]).first()
    row = db.query(InstanceSettings).first()
    full = False
    if row is not None and row.max_registered_users is not None:
        full = count_registered_users(db) >= row.max_registered_users
    return InviteStatusPublic(
        status=invite_public_status(invite),
        registration_mode=row.registration_mode if row is not None else "open",
        full=full,
    )


@invites_router.get("/invites/{token}", response_model=InviteLinkPublic)
async def get_invite_public(
    token: str,
    request: Request = None,
    db: Session = Depends(get_db),
    cache=Depends(get_redis_client),
) -> InviteLinkPublic:
    """Get invite metadata for the registration page (public, no auth, rate-limited)."""
    await _throttle_public_invite(request, cache, "invite_lookup", INVITE_LOOKUP_LIMIT)
    invite = _resolve_token(token, db)
    return InviteLinkPublic(
        id=str(invite.id),
        # Only what the accept page needs. A code holder learns neither the
        # full bound address, nor the roles, nor the issuer's internal note.
        email=_mask_email(invite.email),
        roles=[],
        expires_at=invite.expires_at,
        note=None,
    )


@invites_router.post("/invites/{token}/accept", response_model=dict, status_code=201)
async def accept_invite(
    token: str,
    payload: InviteAccept,
    db: Session = Depends(get_db),
    request: Request = None,
    cache=Depends(get_redis_client),
) -> dict:
    """
    Accept an invite, provision a Keycloak login, and pre-create the user.

    The invite token is the authorization proof for a NEW account: we spend
    the invite (atomically, inside the admission transaction), create the
    Keycloak login with the chosen password, then create the computor User.
    The login is always created UNVERIFIED with the VERIFY_EMAIL required
    action: Keycloak issues no tokens until the address is confirmed, and
    only then does the first SSO login link to this account by email.

    An existing Computor user — owning the address as primary OR student
    email — is never adopted on the invite alone (computor-org/issues#382
    made that possible, and it let any invite holder take over an unused
    pre-provisioned account, admins included). Adoption needs all of: an
    invite issued for exactly this email, a row that has never signed in,
    holds no staff role, and is neither banned nor archived; the row itself
    is left untouched. Existing Keycloak credentials are never reset, and a
    Keycloak user created here is removed again if the user insert fails.

    Database work runs in the threadpool, and no transaction is open while
    Keycloak is called (see the phases below).
    """
    from computor_backend.business_logic.registration_admission import (
        consume_invite,
        refund_invite,
    )

    await _throttle_public_invite(request, cache, "invite_accept", INVITE_ACCEPT_LIMIT)
    email = payload.email.lower()

    # Three phases so that no database lock is ever held across the Keycloak
    # call (a lock holder suspended on the network, while another request
    # waits on that lock, stalls the worker):
    #   1. check + spend the invite, COMMIT;
    #   2. create the Keycloak login (no transaction open);
    #   3. re-check under the locks + insert/adopt, COMMIT.
    # A failure after 1 refunds the invite; a failure in 3 also deletes the
    # Keycloak user created in 2.

    def _admit():
        invite = _resolve_token(token, db)

        # A referral invite admits through /join (SSO), where the email must
        # be IdP-verified; this path would skip that check.
        if invite.kind == "referral":
            raise BadRequestException(
                detail="This invite is used by signing in from its /join link."
            )
        if invite.email and invite.email.lower() != email:
            raise BadRequestException(
                detail="This invite is restricted to a different email address"
            )
        existing = _check_admission(invite, email, payload.email, db)

        # Spend the invite now, before Keycloak: one conditional UPDATE, so
        # two concurrent accepts of a single-use invite cannot both pass.
        if consume_invite(db, token, email) is None:
            raise BadRequestException(
                detail="This invite has already been used the maximum number of times"
            )
        result = invite.id, invite.created_by, list(invite.roles or []), (
            str(existing.id) if existing else None
        )
        db.commit()
        return result

    async def _in_transaction(fn):
        try:
            return await run_in_threadpool(fn)
        except BaseException:
            await run_in_threadpool(db.rollback)
            raise

    async def _refund():
        def _do():
            refund_invite(db, str(invite_id))
            db.commit()
        try:
            await _in_transaction(_do)
        except Exception as exc:  # noqa: BLE001 - keep the original error
            logger.error(f"Could not refund invite {invite_id}: {exc}")

    invite_id, created_by, invite_roles, existing_id = await _in_transaction(_admit)

    # Provision the Keycloak login (refused if one exists for this email).
    from computor_backend.business_logic.auth import provision_keycloak_login

    try:
        # Never verified: whoever typed the address has not shown they can read
        # it. Keycloak withholds tokens until the VERIFY_EMAIL action is done,
        # and only then can a first SSO login link to or create the account.
        kc_user_id, _ = await provision_keycloak_login(
            email=payload.email,
            password=payload.password,
            given_name=payload.given_name,
            family_name=payload.family_name,
            email_verified=False,
        )
    except BaseException:
        await _refund()
        raise

    def _finish():
        invite = db.query(InviteLink).filter(InviteLink.id == invite_id).one()
        # Re-check under the locks: the cap or the existing row may have
        # changed while Keycloak was being called.
        existing = _check_admission(invite, email, payload.email, db)
        if (existing is None) != (existing_id is None) or (
            existing is not None and str(existing.id) != existing_id
        ):
            raise BadRequestException(detail="The account changed meanwhile; try again.")
        if existing is not None:
            # Left untouched until its owner proves the address; see above.
            user = existing
        else:
            # Email-only, no local password — authentication is via Keycloak.
            user = User(
                email=payload.email,
                given_name=payload.given_name,
                family_name=payload.family_name,
            )
            record_invite(
                user, (str(invite_id), str(created_by) if created_by else None)
            )
            db.add(user)
            db.flush()

        # Assign roles from invite. Admin-conferring roles are re-checked
        # against the creator's CURRENT roles: create_invite already blocks
        # non-admins from minting such invites, but an invite predating that
        # guard (or whose creator has since lost admin) must not remain a
        # stored escalation. The other roles are still granted.
        roles_to_grant = list(invite_roles)
        admin_roles = [r for r in roles_to_grant if grants_system_admin(r)]
        if admin_roles and not _creator_is_admin(invite, db):
            logger.warning(
                f"Invite {invite_id}: skipping admin role(s) {admin_roles} — "
                f"creator {created_by} is not an admin"
            )
            roles_to_grant = [r for r in roles_to_grant if not grants_system_admin(r)]
        held = {
            row[0]
            for row in db.query(UserRole.role_id).filter(UserRole.user_id == str(user.id))
        }
        for role_id in roles_to_grant:
            if role_id not in held:
                db.add(UserRole(user_id=str(user.id), role_id=role_id))
        user_id = str(user.id)
        db.commit()
        return user_id

    try:
        user_id = await _in_transaction(_finish)
    except BaseException:
        # Remove the Keycloak login THIS request created, so no credential
        # survives for an address the user row does not own, and give the
        # invite back.
        await _delete_created_keycloak_user(kc_user_id)
        await _refund()
        raise

    if existing_id:
        logger.info(f"User {user_id} adopted via invite {invite_id} (pending email verification)")
    else:
        logger.info(f"User {user_id} pre-created via invite {invite_id}")

    return {
        "user_id": user_id,
        "email": payload.email,
        "adopted": existing_id is not None,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check_admission(invite: InviteLink, email: str, typed_email: str, db: Session) -> Optional[User]:
    """Refuse unless this invite may create (or adopt) the owner of ``email``.

    Returns the existing user to adopt, or None for a brand-new account (for
    which instance_settings is locked and the mode/cap checked).
    """
    from computor_backend.business_logic.registration_admission import user_is_staff
    from computor_backend.business_logic.user_lifecycle import login_evidence

    existing = _user_owning_email(email, db)
    if existing:
        if not invite.email:
            raise BadRequestException(
                detail="An account for this email address already exists. Only an "
                "invite issued for this address can activate it; ask an administrator."
            )
        if login_evidence(str(existing.id), db):
            raise BadRequestException(
                detail=f"An account for '{typed_email}' already exists and has been "
                "signed in to. Please sign in instead of using the invite."
            )
        if existing.banned_at is not None:
            raise BadRequestException(detail="This account is banned and cannot be activated")
        if existing.archived_at is not None:
            raise BadRequestException(
                detail="This account is archived. Ask an administrator to unarchive it first."
            )
        if user_is_staff(db, str(existing.id)):
            raise BadRequestException(
                detail="This account cannot be activated through an invite."
            )
        return existing
    # A brand-new user: registration mode and the hard user cap apply exactly
    # as on the first-SSO-login path (locks instance_settings).
    row = check_registration_capacity(db)
    # While registration is gated, an invite not bound to an address must go
    # through /join, where the IdP verifies the email.
    if row is not None and row.registration_mode != "open" and not invite.email:
        raise BadRequestException(
            detail="This invite is used by signing in from its /join link."
        )
    return None


def _mask_email(email: Optional[str]) -> Optional[str]:
    """'jane.doe@example.org' -> 'j***@example.org' (None stays None)."""
    if not email:
        return None
    local, _, domain = email.partition("@")
    return f"{local[:1]}***@{domain}" if domain else "***"


def _user_owning_email(email: str, db: Session) -> Optional[User]:
    """The user that owns ``email`` as primary OR student-profile address.

    Mirrors the SSO first-login lookup (and the case-insensitive uniqueness
    trigger across both columns): an address that is some user's student
    email belongs to that user, and must get the same protection.
    """
    from computor_backend.model.auth import StudentProfile

    user = db.query(User).filter(func.lower(User.email) == email).first()
    if user is not None:
        return user
    owners = {
        uid
        for (uid,) in db.query(StudentProfile.user_id)
        .filter(func.lower(StudentProfile.student_email) == email)
        .distinct()
    }
    if len(owners) > 1:
        raise BadRequestException(
            detail="This email address is ambiguous; ask an administrator."
        )
    if owners:
        return db.query(User).filter(User.id == next(iter(owners))).first()
    return None


async def _delete_created_keycloak_user(kc_user_id: Optional[str]) -> None:
    """Best-effort removal of a Keycloak user created by this very request."""
    if not kc_user_id:
        return
    from computor_backend.auth.keycloak_admin import KeycloakAdminClient

    try:
        await KeycloakAdminClient().delete_user(kc_user_id)
        logger.info(f"Removed Keycloak user {kc_user_id} after a failed invite acceptance")
    except Exception as exc:  # noqa: BLE001 - the original error matters more
        logger.error(f"Could not remove Keycloak user {kc_user_id}: {exc}")


def _creator_is_admin(invite: InviteLink, db: Session) -> bool:
    """True if the invite's creator currently holds an admin-conferring role."""
    if not invite.created_by:
        return False
    rows = db.query(UserRole.role_id).filter(UserRole.user_id == invite.created_by).all()
    return any(grants_system_admin(row[0]) for row in rows)


def _resolve_token(token: str, db: Session) -> InviteLink:
    """Validate a token and return the InviteLink, raising on any problem."""
    invite = db.query(InviteLink).filter(InviteLink.token == token).first()
    if not invite:
        raise NotFoundException(detail="Invite not found or invalid")
    if invite.revoked_at is not None:
        raise BadRequestException(detail="This invite has been revoked")
    now = datetime.now(timezone.utc)
    exp = invite.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if now > exp:
        raise BadRequestException(detail="This invite has expired")
    if invite.use_count >= invite.max_uses:
        raise BadRequestException(detail="This invite has already been used the maximum number of times")
    return invite


def _to_get(invite: InviteLink) -> InviteLinkGet:
    return InviteLinkGet(
        id=str(invite.id),
        token=invite.token,
        created_by=str(invite.created_by) if invite.created_by else None,
        email=invite.email,
        max_uses=invite.max_uses,
        use_count=invite.use_count,
        expires_at=invite.expires_at,
        roles=invite.roles or [],
        note=invite.note,
        kind=invite.kind or "admin",
        revoked_at=invite.revoked_at,
        created_at=invite.created_at,
        updated_at=invite.updated_at,
    )


def _to_list(invite: InviteLink) -> InviteLinkList:
    return InviteLinkList(
        id=str(invite.id),
        token=invite.token,
        email=invite.email,
        max_uses=invite.max_uses,
        use_count=invite.use_count,
        expires_at=invite.expires_at,
        roles=invite.roles or [],
        note=invite.note,
        kind=invite.kind or "admin",
        revoked_at=invite.revoked_at,
        created_at=invite.created_at,
    )
