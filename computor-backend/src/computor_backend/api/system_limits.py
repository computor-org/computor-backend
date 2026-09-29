"""Deployment-wide admission limits — read and write (#351).

``GET /system/limits`` and ``PUT /system/limits`` over the ``instance_settings``
singleton, so the two caps can be turned during a running workshop instead of
being baked into the image.

Read is open to any authenticated user, deliberately: a student who has just
been refused a workspace needs to be able to see that the instance is full and
that it is not their account that is broken. There is nothing sensitive in the
numbers — two counts and two ceilings, no identities, no host detail.

Write is admin-only.

The enforcement of both limits lives in
``business_logic/instance_limits.py``; this module only stores and reports.
"""
import logging
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from computor_backend.business_logic.instance_limits import (
    DEFAULT_LOGIN_IDLE_MINUTES,
    active_workspace_owners,
    count_login_seats,
    instance_settings_row,
    local_install_url,
)
from computor_backend.business_logic.registration_admission import (
    count_registered_users,
)
from computor_backend.coder.client import CoderClient, get_coder_client
from computor_backend.coder.config import get_coder_settings
from computor_backend.database import get_db
from computor_backend.exceptions import BadRequestException, ForbiddenException
from computor_backend.model.course import Course
from computor_backend.model.instance import InstanceSettings
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.core import check_admin
from computor_backend.permissions.principal import Principal
from computor_types.system_limits import (
    InstanceLimitsGet,
    InstanceLimitsUpdate,
    InstanceLimitsUsage,
)

logger = logging.getLogger(__name__)

system_limits_router = APIRouter()


async def _workspace_user_count(client: CoderClient) -> Optional[int]:
    """Distinct users holding an active workspace, or None if Coder won't say.

    None rather than 0 on failure: an admin reading "0 of 20 in use" while
    Coder is down would take exactly the wrong action.
    """
    if not get_coder_settings().enabled:
        return None
    try:
        workspaces = await client.list_all_workspaces()
    except Exception as e:
        logger.warning(f"Could not count workspace users: {e}")
        return None
    return len(active_workspace_owners(workspaces))


@system_limits_router.get("", response_model=InstanceLimitsGet)
async def get_instance_limits(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    client: Annotated[CoderClient, Depends(get_coder_client)],
) -> InstanceLimitsGet:
    """The configured limits and what they currently measure.

    Any authenticated user may read this — it is the explanation behind a
    refusal, and withholding it would leave the refusal looking like a bug.
    """
    return await _limits_response(instance_settings_row(db), db, client)


@system_limits_router.put("", response_model=InstanceLimitsGet)
async def update_instance_limits(
    request: InstanceLimitsUpdate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    client: Annotated[CoderClient, Depends(get_coder_client)],
) -> InstanceLimitsGet:
    """Replace the stored limits. Admin only; effective on the next request.

    Both limits take effect immediately for new admissions and never evict
    anyone already inside: lowering the cap below the current usage stops the
    next arrival, it does not stop anybody's running workspace or sign a user
    out mid-session.
    """
    if not check_admin(permissions):
        raise ForbiddenException(
            detail="Only administrators may change the instance limits.",
        )

    # The whole transaction runs in the threadpool: waiting on the
    # instance_settings row lock (held by a concurrent admission) must not
    # block the event loop that admission needs in order to finish.
    def _write():
        try:
            return _write_limits(request, permissions, db)
        except BaseException:
            db.rollback()
            raise

    row = await run_in_threadpool(_write)
    return await _limits_response(row, db, client)


def _write_limits(
    request: InstanceLimitsUpdate, permissions: Principal, db: Session
) -> InstanceSettings:
    row = instance_settings_row(db)
    if row is None:
        row = InstanceSettings(singleton=1, created_by=permissions.user_id)
        db.add(row)
    row.max_workspace_users = request.max_workspace_users
    row.max_concurrent_logins = request.max_concurrent_logins
    row.login_idle_minutes = request.login_idle_minutes
    # The registration fields are replaced only when sent, so a client that
    # predates them cannot silently reopen registration with a PUT.
    sent = request.model_fields_set
    if "registration_mode" in sent:
        row.registration_mode = request.registration_mode
    if "max_registered_users" in sent:
        row.max_registered_users = request.max_registered_users
    if "referral_invites_per_user" in sent:
        row.referral_invites_per_user = request.referral_invites_per_user
    if "pilot_course_ids" in sent:
        row.pilot_course_ids = _validated_course_ids(request.pilot_course_ids, db)
    row.updated_by = permissions.user_id
    db.commit()
    db.refresh(row)
    return row


def _validated_course_ids(course_ids: List[str], db: Session) -> List[str]:
    """Reject unknown or non-public pilot courses now rather than at sign-up."""
    ids = list(dict.fromkeys(str(c) for c in course_ids))
    if not ids:
        return []
    try:
        found = {
            str(c)
            for (c,) in db.query(Course.id).filter(Course.id.in_(ids), Course.public.is_(True))
        }
    except Exception:
        db.rollback()
        found = set()
    missing = [c for c in ids if c not in found]
    if missing:
        raise BadRequestException(
            detail=f"Pilot courses must exist and be public: {', '.join(missing)}",
        )
    return ids


async def _limits_response(
    row: Optional[InstanceSettings], db: Session, client: CoderClient
) -> InstanceLimitsGet:
    idle_minutes = row.login_idle_minutes if row is not None else DEFAULT_LOGIN_IDLE_MINUTES
    workspace_users = await _workspace_user_count(client)
    return InstanceLimitsGet(
        max_workspace_users=row.max_workspace_users if row is not None else None,
        max_concurrent_logins=row.max_concurrent_logins if row is not None else None,
        login_idle_minutes=int(idle_minutes),
        local_install_url=local_install_url(),
        registration_mode=row.registration_mode if row is not None else "open",
        max_registered_users=row.max_registered_users if row is not None else None,
        referral_invites_per_user=(
            int(row.referral_invites_per_user) if row is not None else 2
        ),
        pilot_course_ids=[str(c) for c in (row.pilot_course_ids or [])] if row is not None else [],
        usage=InstanceLimitsUsage(
            workspace_users=workspace_users or 0,
            workspace_users_available=workspace_users is not None,
            login_seats=await count_login_seats(int(idle_minutes) * 60),
            registered_users=count_registered_users(db),
        ),
    )
