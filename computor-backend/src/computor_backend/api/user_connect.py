"""Connect a pre-provisioned user to a real (logged-in) user.

Admins and ``_user_manager`` role holders can absorb a user row that was
created by a course roster import (CSV / by-email) — and that has never been
logged into — into the person's real account, moving memberships, student
profiles and everything else across and deleting the emptied row. See
``business_logic/user_connect.py`` for the merge semantics.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from computor_backend.business_logic.user_connect import connect_users
from computor_backend.database import get_db
from computor_backend.exceptions import ForbiddenException
from computor_backend.model.role import UserRole
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_types.users import UserConnectRequest, UserConnectResponse

logger = logging.getLogger(__name__)

user_connect_router = APIRouter()


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


@user_connect_router.post("/users/{user_id}/connect", response_model=UserConnectResponse)
async def connect_user(
    user_id: str,
    payload: UserConnectRequest,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
) -> UserConnectResponse:
    """Absorb a pre-provisioned user into this user (admin or _user_manager).

    ``user_id`` is the keeper — the real account. The request names the
    source user to absorb; that row is deleted on success. Refused (409)
    unless the source user has never authenticated. With ``dry_run`` the
    validated merge plan is returned and nothing changes.
    """
    _require_user_manager(principal, db)

    result = connect_users(
        target_user_id=user_id,
        source_user_id=payload.source_user_id,
        dry_run=payload.dry_run,
        db=db,
    )

    if not result.dry_run:
        logger.info(
            "User %s connected pre-provisioned user %s into %s",
            principal.user_id,
            result.source_user_id,
            result.target_user_id,
        )
        # Same invalidation the member import performs: the keeper's cached
        # course lists (tagged user:<uid>) and the per-course roster views
        # would otherwise hide the moved memberships until TTL expiry.
        try:
            from computor_backend.cache import get_cache

            cache = get_cache()
            cache.invalidate_user_views(user_id=result.target_user_id)
            cache.invalidate_user_views(user_id=result.source_user_id)
            for move in result.course_memberships:
                cache.invalidate_user_views(entity_type="course_id", entity_id=move.course_id)
                for view_tag in ("student_view", "tutor_view", "lecturer_view"):
                    cache.invalidate_user_views(entity_type=view_tag, entity_id=move.course_id)
        except Exception as cache_err:
            logger.warning(f"View cache invalidation after user connect failed: {cache_err}")

    return result
