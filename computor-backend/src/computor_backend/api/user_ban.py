"""User ban / unban endpoints.

Admins and ``_user_manager`` role holders can ban a user, which blocks them from
authenticating. Enforcement is two-layered: ``banned_at`` on the user row is the
durable source of truth (checked in ``PrincipalBuilder.build`` on every cache
miss / fresh auth and in the SSO callback), while a Redis kill-switch flag makes
the ban take effect immediately even against a warm auth cache.

Admin users cannot be banned (mirrors the archive guard); a caller cannot ban
themselves. Service accounts are bannable.
"""

import logging
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from computor_backend.business_logic.users import get_current_user
from computor_backend.database import get_db
from computor_backend.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from computor_backend.model.auth import User
from computor_backend.model.role import UserRole
from computor_backend.permissions.auth import (
    clear_user_banned,
    get_current_principal,
    mark_user_banned,
)
from computor_backend.permissions.principal import Principal
from computor_types.users import UserBanRequest, UserGet

logger = logging.getLogger(__name__)

user_ban_router = APIRouter()


def _require_user_manager(principal: Principal, db: Session) -> None:
    """Raise ForbiddenException unless caller is admin or has _user_manager role."""
    if principal.is_admin:
        return
    role = (
        db.query(UserRole)
        .filter(UserRole.user_id == principal.user_id, UserRole.role_id == "_user_manager")
        .first()
    )
    if not role:
        raise ForbiddenException(detail="Requires _admin or _user_manager role")


def _load_target(user_id: str, db: Session) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise NotFoundException(detail="User not found")
    return user


@user_ban_router.patch("/users/{user_id}/ban", response_model=UserGet)
async def ban_user(
    user_id: str,
    principal: Annotated[Principal, Depends(get_current_principal)],
    payload: Optional[UserBanRequest] = None,
    db: Session = Depends(get_db),
) -> UserGet:
    """Ban a user, blocking them from authenticating (admin or _user_manager).

    Stamps ``banned_at`` (source of truth) plus an optional ``ban_reason`` and
    sets the Redis kill-switch so any warm auth cache is invalidated at once.
    Rejects self-bans and bans against ``_admin`` users.
    """
    _require_user_manager(principal, db)
    user = _load_target(user_id, db)

    if str(user.id) == str(principal.user_id):
        raise BadRequestException(detail="You cannot ban yourself")

    target_is_admin = (
        db.query(UserRole)
        .filter(UserRole.user_id == user.id, UserRole.role_id == "_admin")
        .first()
        is not None
    )
    if target_is_admin:
        raise ForbiddenException(detail="Admin users cannot be banned")

    if user.banned_at is None:
        user.banned_at = datetime.now(timezone.utc)
    user.ban_reason = payload.reason if payload else None
    db.commit()

    await mark_user_banned(str(user.id))
    logger.info("User %s banned by %s", user.id, principal.user_id)

    return get_current_user(str(user.id), db)


@user_ban_router.patch("/users/{user_id}/unban", response_model=UserGet)
async def unban_user(
    user_id: str,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
) -> UserGet:
    """Lift a user's ban (admin or _user_manager)."""
    _require_user_manager(principal, db)
    user = _load_target(user_id, db)

    user.banned_at = None
    user.ban_reason = None
    db.commit()

    await clear_user_banned(str(user.id))
    logger.info("User %s unbanned by %s", user.id, principal.user_id)

    return get_current_user(str(user.id), db)
