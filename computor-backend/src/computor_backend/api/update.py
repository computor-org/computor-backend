"""
Self-update API endpoints (System -> Updates admin page).

Compares the running git commit against the tip of the deployment repository
(SYSTEM_REPO_URL / SYSTEM_REPO_BRANCH from .env) and exposes the state of the
updater sidecar. The API only reads/queues — the actual update is executed by
the updater sidecar (see ops/lib/update.sh), never by this process.
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Annotated, Optional, Tuple
from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from computor_backend.config import get_settings
from computor_backend.database import get_db
from computor_backend.exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
)
from computor_backend.model.auth import User
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.core import check_admin
from computor_backend.permissions.principal import Principal
from computor_backend.redis_cache import get_redis_client
from computor_types.update import (
    SystemUpdateState,
    SystemUpdateStatusGet,
    SystemUpdateTriggerResponse,
)

logger = logging.getLogger(__name__)

update_router = APIRouter()

REDIS_KEY_REMOTE = "update:remote"
REDIS_KEY_STATE = "update:state"
REDIS_KEY_AGENT = "update:agent"
REDIS_KEY_LOCK = "update:lock"
REDIS_KEY_QUEUE = "update:queue"

REMOTE_CACHE_TTL = 300  # seconds
LS_REMOTE_TIMEOUT = 10  # seconds
UPDATE_LOCK_TTL = 7200  # seconds — matches ops/lib/update.sh

# Resolved once per process: the running commit/branch never change while the
# process lives (env is baked at image build; dev reads the working tree).
_running_version: Optional[Tuple[str, str]] = None


def _get_running_version() -> Tuple[str, str]:
    """(commit, branch) of the running code: baked env, else git discovery."""
    global _running_version
    if _running_version is not None:
        return _running_version

    settings = get_settings().update
    if settings.git_commit:
        _running_version = (settings.git_commit, settings.git_branch or "unknown")
        return _running_version

    # Dev fallback: the API runs from a git working tree on the host.
    try:
        import git

        repo = git.Repo(__file__, search_parent_directories=True)
        commit = repo.head.commit.hexsha
        try:
            branch = repo.active_branch.name
        except TypeError:  # detached HEAD
            branch = "detached"
        _running_version = (commit, branch)
    except Exception:
        _running_version = ("unknown", "unknown")
    return _running_version


def _sanitize(text: str) -> str:
    """Strip credentials from git output before it is stored or logged."""
    token = get_settings().update.repo_token
    if token:
        text = text.replace(token, "***")
    return re.sub(r"://[^/@\s]+@", "://***@", text)


def sanitized_repo_url() -> str:
    return _sanitize(get_settings().update.repo_url)


async def _ls_remote() -> Tuple[Optional[str], Optional[str]]:
    """(commit, error) of the tracked branch's tip via `git ls-remote`.

    The token never appears in argv or the URL: git resolves credentials
    through an inline helper that reads SYSTEM_REPO_TOKEN from the subprocess
    environment at call time.
    """
    settings = get_settings().update
    ref = f"refs/heads/{settings.repo_branch}"
    argv = ["git"]
    env = {
        "GIT_TERMINAL_PROMPT": "0",  # fail instead of prompting on bad auth
        "HOME": "/tmp",              # ignore any host/user git config
    }
    if settings.repo_token:
        argv += [
            "-c",
            # Literal $SYSTEM_REPO_TOKEN — expanded by the helper's shell from
            # the subprocess env, so the secret is never in the command line.
            'credential.helper=!f() { echo "username=oauth2"; echo "password=$SYSTEM_REPO_TOKEN"; }; f',
        ]
        env["SYSTEM_REPO_TOKEN"] = settings.repo_token
    argv += ["ls-remote", settings.repo_url, ref]

    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=LS_REMOTE_TIMEOUT)
    except asyncio.TimeoutError:
        proc.kill()
        return None, f"git ls-remote timed out after {LS_REMOTE_TIMEOUT}s"
    except FileNotFoundError:
        return None, "git is not installed in this environment"
    except Exception as e:
        return None, _sanitize(str(e))

    if proc.returncode != 0:
        return None, _sanitize(stderr.decode(errors="replace").strip())

    for line in stdout.decode(errors="replace").splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == ref:
            return parts[0], None
    return None, f"branch '{settings.repo_branch}' not found on remote"


async def _get_remote_state(redis, force_refresh: bool) -> dict:
    """Cached remote tip; refreshes via ls-remote when stale or forced."""
    if not force_refresh:
        cached = await redis.hgetall(REDIS_KEY_REMOTE)
        if cached:
            return cached

    settings = get_settings().update
    if not settings.repo_url:
        return {"error": "SYSTEM_REPO_URL is not configured in .env"}

    commit, error = await _ls_remote()
    state = {
        "commit": commit or "",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "error": error or "",
    }
    await redis.hset(REDIS_KEY_REMOTE, mapping=state)
    await redis.expire(REDIS_KEY_REMOTE, REMOTE_CACHE_TTL)
    if error:
        logger.warning(f"Update check against {sanitized_repo_url()} failed: {error}")
    return state


async def _build_status(redis, force_refresh: bool = False) -> SystemUpdateStatusGet:
    settings = get_settings().update
    running_commit, running_branch = _get_running_version()
    remote = await _get_remote_state(redis, force_refresh)
    raw_state = await redis.hgetall(REDIS_KEY_STATE)
    updater_online = bool(await redis.exists(REDIS_KEY_AGENT))

    remote_commit = remote.get("commit") or None
    return SystemUpdateStatusGet(
        update_enabled=settings.enabled,
        running_commit=running_commit,
        running_branch=running_branch,
        repo_url=sanitized_repo_url(),
        tracked_branch=settings.repo_branch,
        remote_commit=remote_commit,
        remote_checked_at=remote.get("checked_at") or None,
        remote_error=remote.get("error") or None,
        update_available=bool(
            remote_commit
            and running_commit not in ("", "unknown")
            and remote_commit != running_commit
        ),
        updater_online=updater_online,
        state=SystemUpdateState(**raw_state) if raw_state else SystemUpdateState(),
    )


# --- Endpoints ---


@update_router.get("/status", response_model=SystemUpdateStatusGet)
async def get_update_status(
    permissions: Annotated[Principal, Depends(get_current_principal)],
):
    """
    Get the running version, the tracked remote's tip, and update state.

    Admin only. The remote tip is cached in Redis for 5 minutes.
    """
    if not check_admin(permissions):
        raise ForbiddenException(detail="Admin privileges required")

    redis = await get_redis_client()
    return await _build_status(redis)


@update_router.post("/check", response_model=SystemUpdateStatusGet)
async def check_for_update(
    permissions: Annotated[Principal, Depends(get_current_principal)],
):
    """
    Force-refresh the remote tip (ignores the cache) and return the status.

    Admin only. Powers the "Check now" button.
    """
    if not check_admin(permissions):
        raise ForbiddenException(detail="Admin privileges required")

    redis = await get_redis_client()
    return await _build_status(redis, force_refresh=True)


@update_router.post("", response_model=SystemUpdateTriggerResponse)
async def trigger_update(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """
    Queue a self-update run.

    Admin only. The API only queues — the updater sidecar picks the request up
    from Redis and executes it (maintenance page -> git update -> rebuild ->
    restart -> health check, with automatic rollback on failure). Expect the
    whole system, including this API, to go down for several minutes.
    """
    if not check_admin(permissions):
        raise ForbiddenException(detail="Admin privileges required")

    settings = get_settings().update
    if not settings.enabled:
        raise BadRequestException(
            detail="Self-update is disabled. Set UPDATE_ENABLED=true in .env and restart."
        )

    redis = await get_redis_client()
    if not await redis.exists(REDIS_KEY_AGENT):
        raise ConflictException(
            detail="The updater sidecar is not running (development environment, "
            "or the sidecar is down). Updates can only be triggered in production."
        )

    # Single-flight: the lock is released by the updater when the run finishes
    # (or expires after UPDATE_LOCK_TTL as a stuck-run backstop).
    acquired = await redis.set(REDIS_KEY_LOCK, str(uuid4()), nx=True, ex=UPDATE_LOCK_TTL)
    if not acquired:
        raise ConflictException(detail="An update is already in progress.")

    now = datetime.now(timezone.utc).isoformat()
    user = db.query(User).filter(User.id == permissions.user_id).first()
    display_name = (
        f"{user.given_name} {user.family_name}"
        if user and user.given_name
        else permissions.user_id
    )

    # Fresh state for this run (clears any previous run's leftover fields).
    await redis.delete(REDIS_KEY_STATE)
    await redis.hset(REDIS_KEY_STATE, mapping={
        "status": "requested",
        "phase": "",
        "message": "Waiting for the updater to pick up the request",
        "requested_by": permissions.user_id,
        "requested_by_name": display_name,
        "requested_at": now,
        "error": "",
    })
    await redis.lpush(REDIS_KEY_QUEUE, json.dumps({
        "requested_by": permissions.user_id,
        "requested_at": now,
        "branch": settings.repo_branch,
    }))

    logger.warning(f"Self-update REQUESTED by {permissions.user_id} (branch {settings.repo_branch})")

    return SystemUpdateTriggerResponse(status="requested", requested_at=now)


@update_router.post("/reset")
async def reset_update_state(
    permissions: Annotated[Principal, Depends(get_current_principal)],
):
    """
    Clear a stuck update lock/state (admin recovery).

    Marks a non-terminal run as failed and releases the lock so a new update
    can be requested. Does NOT stop a runner that is actually still executing —
    use this only when a run died without cleaning up (the lock also expires
    on its own after 2 hours).
    """
    if not check_admin(permissions):
        raise ForbiddenException(detail="Admin privileges required")

    redis = await get_redis_client()
    state = await redis.hgetall(REDIS_KEY_STATE)
    now = datetime.now(timezone.utc).isoformat()

    await redis.delete(REDIS_KEY_LOCK, REDIS_KEY_QUEUE)
    if state and state.get("status") in ("requested", "running"):
        await redis.hset(REDIS_KEY_STATE, mapping={
            "status": "failed",
            "error": "Manually reset by an administrator.",
            "finished_at": now,
        })

    logger.warning(f"Self-update state RESET by {permissions.user_id}")

    return {"status": "reset"}
