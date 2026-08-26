"""Deployment-wide admission limits (#351).

Two limits, both stored in the ``instance_settings`` singleton so an operator
can turn them during a running workshop:

- **max_workspace_users** — the number of DISTINCT users that may hold an
  active Coder workspace at once. Not a workspace count: a user who already
  has one workspace running has already spent their seat and is never refused
  a second.
- **max_concurrent_logins** — the number of DISTINCT users that may be signed
  in at once. Also per-user, so two tabs are one seat.

Both exempt staff. That is the whole reason they exist separately from
``WorkspaceTemplateSettings.max_running_workspaces``: the per-template quota
models a HARD external constraint (MATLAB licence seats) and therefore binds
admins too, because exceeding it would break the licence server no matter who
did it. These two model soft host capacity, and locking the operator out of
their own instance during an incident is the failure mode #351 is about.

Login seats live in Redis, not in the ``session`` table: the SSO login path
(``business_logic/auth.py``) writes ``sso_session:<hash>`` keys and never
inserts a Session row, so counting that table would always return zero. The
seat index is a sorted set — member = user id, score = epoch seconds of the
user's last authenticated request — which makes "distinct users active within
N minutes" a single ``ZCOUNT`` rather than a keyspace scan.
"""
import logging
import os
import time
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from computor_backend.exceptions import ConflictException, ForbiddenException
from computor_backend.model.instance import InstanceSettings
from computor_backend.model.role import UserRole
from computor_backend.permissions.principal import Principal

logger = logging.getLogger(__name__)


# Builtin roles whose holders bypass both limits: an operator must never be
# locked out of the instance they are trying to fix. Listed explicitly rather
# than derived from the "_" prefix because ``_workspace_user`` is builtin too
# and is held by ordinary students — deriving it would exempt everyone.
STAFF_BYPASS_ROLES = frozenset({
    "_admin",
    "_user_manager",
    "_organization_manager",
    "_service_manager",
    "_example_manager",
    "_git_manager",
    "_workspace_maintainer",
})

# Sorted set of login seats: member = user id, score = last-seen epoch seconds.
LOGIN_SEATS_KEY = "login_seats"

# Used when no instance_settings row exists yet (fresh deployment, or an
# operator who never opened the page). Both limits off, so the behaviour is
# exactly what it was before this module existed.
DEFAULT_LOGIN_IDLE_MINUTES = 30


def instance_settings_row(db: Session) -> Optional[InstanceSettings]:
    """The singleton row, or None when the operator has never set the limits."""
    return db.query(InstanceSettings).first()


def login_idle_seconds(db: Session) -> int:
    row = instance_settings_row(db)
    minutes = row.login_idle_minutes if row is not None else DEFAULT_LOGIN_IDLE_MINUTES
    return int(minutes) * 60


def local_install_url() -> Optional[str]:
    """Download URL for the local VS Code extension, quoted in both refusals.

    Read from the environment on each call rather than cached: it is the one
    piece of a refusal an operator may want to fix without a restart. Read
    directly rather than through ``settings`` for the same reason (the settings
    singleton snapshots the environment at import time).
    """
    return os.environ.get("EXTENSION_PUBLIC_DOWNLOAD_URL") or None


def _local_install_hint() -> str:
    """The "work locally instead" half of a refusal.

    A refusal that only says "full" tells the user to come back later; #351
    asks it to tell them what to do now.
    """
    url = local_install_url()
    if url:
        return (
            " You can keep working without a workspace by installing the Computor "
            f"extension in your own VS Code: {url}"
        )
    return (
        " You can keep working without a workspace by installing the Computor "
        "extension in your own VS Code and cloning your repository locally."
    )


# -----------------------------------------------------------------------------
# Staff bypass
# -----------------------------------------------------------------------------

def principal_is_staff(principal: Principal) -> bool:
    """Whether this caller bypasses both limits.

    Service accounts count as staff: the testing workers and the tutor agent
    authenticate with API tokens, and an admission limit that starves them
    would take the whole course down rather than shed load.
    """
    if principal.is_admin or principal.is_service:
        return True
    return any(role in STAFF_BYPASS_ROLES for role in principal.roles)


def user_is_staff(db: Session, user_id: str) -> bool:
    """Staff check for a user who is not the caller.

    Needed by the lecturer bulk-provisioning path, where the seat being spent
    belongs to the student, not to the lecturer clicking the button.
    """
    roles = (
        db.query(UserRole.role_id)
        .filter(UserRole.user_id == str(user_id))
        .all()
    )
    return any(role_id in STAFF_BYPASS_ROLES for (role_id,) in roles)


# -----------------------------------------------------------------------------
# Workspace-user limit
# -----------------------------------------------------------------------------

def active_workspace_owners(
    workspaces: Iterable, exclude_workspace_id: Optional[str] = None
) -> set[str]:
    """Coder usernames owning a running or starting workspace.

    Counted by the same rule as the per-template quota
    (``course_workspaces.ACTIVE_BUILD_STATUSES``) so the two limits never
    disagree about what "active" means.
    """
    # Imported here: course_workspaces imports this module for the cap itself,
    # and a module-level import would close the cycle.
    from computor_backend.business_logic.course_workspaces import ACTIVE_BUILD_STATUSES

    owners: set[str] = set()
    for workspace in workspaces:
        if exclude_workspace_id and workspace.id == exclude_workspace_id:
            continue
        if workspace.latest_build_transition != "start":
            continue
        status = (
            workspace.latest_build_status.value if workspace.latest_build_status else ""
        )
        if status in ACTIVE_BUILD_STATUSES and workspace.owner_name:
            owners.add(workspace.owner_name)
    return owners


def enforce_workspace_user_cap(
    db: Session,
    workspaces: Iterable,
    owner_username: Optional[str],
    is_staff: bool,
    exclude_workspace_id: Optional[str] = None,
) -> None:
    """Refuse a provision/start that would admit one workspace user too many.

    ``owner_username`` is the Coder username the workspace belongs to — the
    target user, which is not the caller on the lecturer bulk-provisioning
    path. A user already among the active owners is admitted: their seat is
    spent, and refusing them a second workspace would enforce a limit nobody
    asked for.

    Soft, like the template quota: two racing provisions can both pass. The
    consequence is one workspace over the line until the next stop, which is
    the right trade against serializing every launch.
    """
    row = instance_settings_row(db)
    if row is None or row.max_workspace_users is None:
        return
    if is_staff:
        return

    limit = int(row.max_workspace_users)
    owners = active_workspace_owners(workspaces, exclude_workspace_id)
    if owner_username and owner_username in owners:
        return
    if len(owners) < limit:
        return

    raise ConflictException(
        detail=(
            f"This Computor instance is at its capacity of {limit} concurrent "
            f"workspace user(s) ({len(owners)} currently active). Your workspace "
            "cannot be started until someone stops theirs."
            + _local_install_hint()
        ),
    )


# -----------------------------------------------------------------------------
# Concurrent-login limit
# -----------------------------------------------------------------------------

async def touch_login_seat(user_id: str, idle_seconds: int) -> None:
    """Mark the user as active now, and drop seats that went idle.

    Called on login and on every principal-cache miss. That miss happens at
    most every ``AUTH_CACHE_TTL`` (900s) for an actively used client, which is
    why the idle window is constrained to at least a minute and documented as
    "keep above 15": a window shorter than the re-authentication interval would
    evict users who are still working.

    Best-effort. A Redis failure must never cost someone their login, so
    everything here is swallowed — the cost is an undercount, which fails open.
    """
    try:
        from computor_backend.redis_cache import get_redis_client

        redis = await get_redis_client()
        now = time.time()
        await redis.zadd(LOGIN_SEATS_KEY, {str(user_id): now})
        # Prune here rather than on a timer: the set only ever grows on this
        # path, so the write that grows it is the right place to shrink it.
        await redis.zremrangebyscore(LOGIN_SEATS_KEY, "-inf", now - idle_seconds)
    except Exception as e:
        logger.warning(f"Could not refresh login seat for user {user_id}: {e}")


async def release_login_seat(user_id: str) -> None:
    """Give the seat back on an explicit logout.

    Not authoritative — a user with another tab open re-takes the seat on their
    next request, which is correct: they are still logged in.
    """
    try:
        from computor_backend.redis_cache import get_redis_client

        redis = await get_redis_client()
        await redis.zrem(LOGIN_SEATS_KEY, str(user_id))
    except Exception as e:
        logger.warning(f"Could not release login seat for user {user_id}: {e}")


async def count_login_seats(idle_seconds: int) -> int:
    """Distinct users active within the idle window. 0 if Redis is unreachable.

    Failing open is deliberate: an unreachable Redis already breaks
    authentication downstream, and turning it into a lockout on top would make
    the outage harder to fix.
    """
    try:
        from computor_backend.redis_cache import get_redis_client

        redis = await get_redis_client()
        # Count by score rather than ZCARD so a stale member left behind by a
        # failed prune cannot inflate the number into a false refusal.
        return int(
            await redis.zcount(LOGIN_SEATS_KEY, time.time() - idle_seconds, "+inf") or 0
        )
    except Exception as e:
        logger.warning(f"Could not count login seats: {e}")
        return 0


async def holds_login_seat(user_id: str, idle_seconds: int) -> bool:
    """Whether this user already occupies a seat (so a re-login is free)."""
    try:
        from computor_backend.redis_cache import get_redis_client

        redis = await get_redis_client()
        score = await redis.zscore(LOGIN_SEATS_KEY, str(user_id))
        return score is not None and float(score) >= time.time() - idle_seconds
    except Exception as e:
        logger.warning(f"Could not read login seat for user {user_id}: {e}")
        return False


async def enforce_login_cap(db: Session, user_id: str) -> None:
    """Refuse a login that would admit one user too many.

    Applies to interactive SSO logins only. API tokens are not logins — a
    service account is infrastructure, and capping it sheds the wrong load.

    A user who already holds a seat always gets through: signing in again from
    a second device must not be treated as a second user, and must not be able
    to fail while the first device still works.
    """
    row = instance_settings_row(db)
    if row is None or row.max_concurrent_logins is None:
        return
    if user_is_staff(db, user_id):
        return

    idle_seconds = int(row.login_idle_minutes) * 60
    if await holds_login_seat(user_id, idle_seconds):
        return

    limit = int(row.max_concurrent_logins)
    seats = await count_login_seats(idle_seconds)
    if seats < limit:
        return

    raise ForbiddenException(
        detail=(
            f"This Computor instance is at its capacity of {limit} concurrent "
            f"user(s) ({seats} currently signed in). Please try again in a few "
            "minutes." + _local_install_hint()
        ),
    )
