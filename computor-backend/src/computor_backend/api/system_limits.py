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
from typing import Annotated, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from computor_backend.business_logic.instance_limits import (
    DEFAULT_LOGIN_IDLE_MINUTES,
    active_workspace_owners,
    count_login_seats,
    instance_settings_row,
    local_install_url,
)
from computor_backend.coder.client import CoderClient, get_coder_client
from computor_backend.coder.config import get_coder_settings
from computor_backend.database import get_db
from computor_backend.exceptions import ForbiddenException
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
    row = instance_settings_row(db)
    idle_minutes = row.login_idle_minutes if row is not None else DEFAULT_LOGIN_IDLE_MINUTES
    workspace_users = await _workspace_user_count(client)
    return InstanceLimitsGet(
        max_workspace_users=row.max_workspace_users if row is not None else None,
        max_concurrent_logins=row.max_concurrent_logins if row is not None else None,
        login_idle_minutes=int(idle_minutes),
        local_install_url=local_install_url(),
        usage=InstanceLimitsUsage(
            workspace_users=workspace_users or 0,
            workspace_users_available=workspace_users is not None,
            login_seats=await count_login_seats(int(idle_minutes) * 60),
        ),
    )


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

    row = instance_settings_row(db)
    if row is None:
        row = InstanceSettings(singleton=1, created_by=permissions.user_id)
        db.add(row)
    row.max_workspace_users = request.max_workspace_users
    row.max_concurrent_logins = request.max_concurrent_logins
    row.login_idle_minutes = request.login_idle_minutes
    row.updated_by = permissions.user_id
    db.commit()
    db.refresh(row)

    workspace_users = await _workspace_user_count(client)
    return InstanceLimitsGet(
        max_workspace_users=row.max_workspace_users,
        max_concurrent_logins=row.max_concurrent_logins,
        login_idle_minutes=int(row.login_idle_minutes),
        local_install_url=local_install_url(),
        usage=InstanceLimitsUsage(
            workspace_users=workspace_users or 0,
            workspace_users_available=workspace_users is not None,
            login_seats=await count_login_seats(int(row.login_idle_minutes) * 60),
        ),
    )
