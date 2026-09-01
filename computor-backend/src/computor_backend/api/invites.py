"""
Invite link API endpoints.

Admins and _user_manager role holders can create invite links.
Invite acceptance is public (no authentication required).
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from computor_backend.database import get_db
from computor_backend.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from computor_backend.model.auth import User
from computor_backend.model.invite import InviteLink
from computor_backend.model.role import Role, UserRole
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.permissions.roles import grants_system_admin
from computor_types.invites import (
    InviteAccept,
    InviteLinkCreate,
    InviteLinkGet,
    InviteLinkList,
    InviteLinkPublic,
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
    _require_invite_manager(principal, db)
    invite = db.query(InviteLink).filter(InviteLink.id == invite_id).first()
    if not invite:
        raise NotFoundException(detail="Invite not found")
    invite.revoked_at = datetime.now(timezone.utc)
    db.commit()
    logger.info(f"Invite {invite_id} revoked by {principal.user_id}")


# ---------------------------------------------------------------------------
# Public endpoints (no authentication required)
# ---------------------------------------------------------------------------

@invites_router.get("/invites/{token}", response_model=InviteLinkPublic)
async def get_invite_public(
    token: str,
    db: Session = Depends(get_db),
) -> InviteLinkPublic:
    """Get invite metadata for the registration page (public, no auth)."""
    invite = _resolve_token(token, db)
    return InviteLinkPublic(
        id=str(invite.id),
        email=invite.email,
        roles=invite.roles or [],
        expires_at=invite.expires_at,
        note=invite.note,
    )


@invites_router.post("/invites/{token}/accept", response_model=dict, status_code=201)
async def accept_invite(
    token: str,
    payload: InviteAccept,
    db: Session = Depends(get_db),
) -> dict:
    """
    Accept an invite, provision a Keycloak login, and pre-create the user.

    The invite token is the authorization proof. We create the Keycloak user
    (with the chosen password) first, then create the computor User. On first
    SSO login Keycloak links to this pre-created account by email.

    A pre-provisioned user (admin-created or roster-imported, never signed in)
    with the same email is ADOPTED instead of rejected — the invite becomes
    the activation path for the existing row, keeping its memberships and
    profile (computor-org/issues#382). Only a user with real login evidence
    blocks the email.
    """
    invite = _resolve_token(token, db)

    # Email restriction check
    if invite.email and invite.email.lower() != payload.email.lower():
        raise BadRequestException(detail="This invite is restricted to a different email address")

    from computor_backend.business_logic.user_lifecycle import login_evidence

    # Case-insensitive: the SSO first-login join lowercases both sides, so an
    # admin-typed "Name@mac.com" row must count as the same identity here too.
    existing = db.query(User).filter(
        func.lower(User.email) == payload.email.lower()
    ).first()
    if existing:
        if login_evidence(str(existing.id), db):
            raise BadRequestException(
                detail=f"An account for '{payload.email}' already exists and has been "
                "signed in to. Please sign in instead of using the invite."
            )
        if existing.banned_at is not None:
            raise BadRequestException(detail="This account is banned and cannot be activated")
        if existing.archived_at is not None:
            raise BadRequestException(
                detail="This account is archived. Ask an administrator to unarchive it first."
            )

    # Provision the Keycloak login first (invite token is the authorization
    # proof). If this fails we neither create the user nor consume the invite.
    from computor_backend.business_logic.auth import provision_keycloak_login
    await provision_keycloak_login(
        email=payload.email,
        password=payload.password,
        given_name=payload.given_name,
        family_name=payload.family_name,
    )

    if existing:
        # Adopt the pre-provisioned row: the person registering owns the
        # identity now, so their chosen name wins over imported placeholders.
        user = existing
        if payload.given_name:
            user.given_name = payload.given_name
        if payload.family_name:
            user.family_name = payload.family_name
    else:
        # Create user (email-only, no local password — authentication is via Keycloak)
        user = User(
            email=payload.email,
            given_name=payload.given_name,
            family_name=payload.family_name,
        )
        db.add(user)
        db.flush()

    # Assign roles from invite. Admin-conferring roles are re-checked
    # against the creator's CURRENT roles: create_invite already blocks
    # non-admins from minting such invites, but an invite predating that
    # guard (or whose creator has since lost admin) must not remain a
    # stored escalation. The other roles are still granted.
    roles_to_grant = list(invite.roles or [])
    admin_roles = [r for r in roles_to_grant if grants_system_admin(r)]
    if admin_roles and not _creator_is_admin(invite, db):
        logger.warning(
            f"Invite {invite.id}: skipping admin role(s) {admin_roles} — "
            f"creator {invite.created_by} is not an admin"
        )
        roles_to_grant = [r for r in roles_to_grant if not grants_system_admin(r)]
    held = {
        row[0]
        for row in db.query(UserRole.role_id).filter(UserRole.user_id == str(user.id))
    }
    for role_id in roles_to_grant:
        if role_id not in held:
            db.add(UserRole(user_id=str(user.id), role_id=role_id))

    # Consume invite
    invite.use_count += 1
    db.commit()

    if existing:
        logger.info(f"User {user.id} ({user.email}) adopted via invite {invite.id}")
    else:
        logger.info(f"User {user.id} ({user.email}) pre-created via invite {invite.id}")

    return {
        "user_id": str(user.id),
        "email": payload.email,
        "adopted": existing is not None,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
        revoked_at=invite.revoked_at,
        created_at=invite.created_at,
    )
