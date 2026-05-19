"""
Invite link API endpoints.

Admins and _user_manager role holders can create invite links.
Invite acceptance is public (no authentication required).
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from computor_backend.database import get_db
from computor_backend.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from computor_backend.model.auth import User
from computor_backend.model.invite import InviteLink
from computor_backend.model.role import UserRole
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_types.invites import (
    InviteAccept,
    InviteLinkCreate,
    InviteLinkGet,
    InviteLinkList,
    InviteLinkPublic,
)
from computor_types.password_utils import create_password_hash, PasswordValidationError

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
        raise ForbiddenException("Requires _admin or _user_manager role")


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
        raise NotFoundException("Invite not found")
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
        raise NotFoundException("Invite not found")
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


@invites_router.post("/invites/{token}/accept", response_model=dict)
async def accept_invite(
    token: str,
    payload: InviteAccept,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> dict:
    """
    Accept an invite and create a new user account.

    On success the response sets HttpOnly cookies (ct_access_token /
    ct_refresh_token) so the browser is immediately authenticated.
    """
    invite = _resolve_token(token, db)

    # Email restriction check
    if invite.email and invite.email.lower() != payload.email.lower():
        raise BadRequestException("This invite is restricted to a different email address")

    # Password confirmation
    if payload.password != payload.confirm_password:
        raise BadRequestException("Passwords do not match")

    # Uniqueness checks
    if db.query(User).filter(User.username == payload.username).first():
        raise BadRequestException(f"Username '{payload.username}' is already taken")
    if db.query(User).filter(User.email == payload.email).first():
        raise BadRequestException(f"Email '{payload.email}' is already registered")

    # Hash password
    try:
        password_hash = create_password_hash(
            payload.password,
            validate=True,
            username=payload.username,
            email=payload.email,
        )
    except PasswordValidationError as e:
        raise BadRequestException(str(e))

    # Create user
    user = User(
        username=payload.username,
        email=payload.email,
        given_name=payload.given_name,
        family_name=payload.family_name,
        password=password_hash,
        password_reset_required=False,
    )
    db.add(user)
    db.flush()  # Get user.id without committing

    # Assign roles from invite
    for role_id in (invite.roles or []):
        db.add(UserRole(user_id=str(user.id), role_id=role_id))

    # Consume invite
    invite.use_count += 1
    db.commit()
    db.refresh(user)

    logger.info(f"User {user.id} ({user.username}) created via invite {invite.id}")

    # Create session (auto-login)
    from computor_backend.utils.client_info import get_client_ip, get_user_agent, make_device_label
    access_token, refresh_token = await _create_session(
        user_id=str(user.id),
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        db=db,
    )

    _set_auth_cookies(response, access_token, refresh_token)

    return {
        "user_id": str(user.id),
        "username": user.username,
        "access_token": access_token,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_token(token: str, db: Session) -> InviteLink:
    """Validate a token and return the InviteLink, raising on any problem."""
    invite = db.query(InviteLink).filter(InviteLink.token == token).first()
    if not invite:
        raise NotFoundException("Invite not found or invalid")
    if invite.revoked_at is not None:
        raise BadRequestException("This invite has been revoked")
    now = datetime.now(timezone.utc)
    exp = invite.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if now > exp:
        raise BadRequestException("This invite has expired")
    if invite.use_count >= invite.max_uses:
        raise BadRequestException("This invite has already been used the maximum number of times")
    return invite


async def _create_session(
    user_id: str,
    ip_address: str,
    user_agent: str,
    db: Session,
) -> tuple[str, str]:
    """Create Redis + DB session for a user. Returns (access_token, refresh_token)."""
    from computor_backend.utils.token_hash import generate_token, hash_token, hash_token_binary
    from computor_backend.utils.client_info import make_device_label
    from computor_backend.repositories.session_repo import SessionRepository
    from computor_backend.redis_cache import get_redis_client
    from computor_backend.model.auth import Session as SessionModel
    from computor_backend.business_logic.auth import ACCESS_TOKEN_TTL, REFRESH_TOKEN_TTL

    access_token = generate_token(32)
    refresh_token = generate_token(32)
    access_token_hash = hash_token(access_token)
    refresh_token_hash_binary = hash_token_binary(refresh_token)

    redis_client = await get_redis_client()
    now = datetime.now(timezone.utc)

    await redis_client.set(
        f"sso_session:{access_token_hash}",
        json.dumps({"user_id": user_id, "provider": "local", "created_at": str(now), "token_type": "access"}),
        ex=ACCESS_TOKEN_TTL,
    )
    await redis_client.set(
        f"refresh_token:{hash_token(refresh_token)}",
        json.dumps({
            "user_id": user_id,
            "provider": "local",
            "created_at": str(now),
            "expires_at": str(now + timedelta(seconds=REFRESH_TOKEN_TTL)),
            "token_type": "refresh",
            "access_token_hash": access_token_hash,
        }),
        ex=REFRESH_TOKEN_TTL,
    )

    session_repo = SessionRepository(db, SessionModel, None)
    session_repo.create(SessionModel(
        user_id=user_id,
        session_id=access_token_hash,
        refresh_token_hash=refresh_token_hash_binary,
        created_ip=ip_address,
        last_ip=ip_address,
        user_agent=user_agent,
        device_label=make_device_label(user_agent),
        expires_at=now + timedelta(seconds=ACCESS_TOKEN_TTL),
        refresh_expires_at=now + timedelta(seconds=REFRESH_TOKEN_TTL),
        properties={"provider": "local", "login_method": "invite"},
    ))

    return access_token, refresh_token


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(key="ct_access_token", value=access_token, httponly=True, secure=False, samesite="lax", max_age=3600)
    response.set_cookie(key="ct_refresh_token", value=refresh_token, httponly=True, secure=False, samesite="lax", max_age=604800)


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
