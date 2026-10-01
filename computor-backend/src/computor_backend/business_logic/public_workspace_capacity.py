"""Durable admission for the public hosted-workspace pool.

A Postgres transaction lock protects each fresh Coder inventory and reservation.
Reservations survive API and Redis restarts and have no guessed expiry: Coder
may queue a build for longer than any local timeout.
"""

import asyncio
import os
import time

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from computor_backend.database import SessionLocal
from computor_backend.exceptions import RateLimitException, ServiceUnavailableException

_LOCK_ID = 743513937149098642
_MAX_FLEET_SIZE = 10000


def required_public_container_limit() -> int | None:
    """Private deployments keep their existing unlimited default."""
    if os.environ.get("COMPUTOR_PUBLIC_DEPLOYMENT", "").strip().lower() != "true":
        return None
    raw = os.environ.get("CODER_MAX_RUNNING_WORKSPACES", "").strip()
    try:
        value = int(raw)
    except ValueError:
        value = 0
    if not 0 < value <= _MAX_FLEET_SIZE:
        raise ServiceUnavailableException(
            detail="Public workspaces require a positive CODER_MAX_RUNNING_WORKSPACES limit"
        )
    return value


def _fleet_record(workspace) -> tuple[bool, bool, str]:
    from computor_backend.business_logic.course_workspaces import ACTIVE_BUILD_STATUSES

    status = workspace.latest_build_status
    status_value = status.value if status is not None else ""
    active = workspace.latest_build_transition == "start" and status_value in ACTIVE_BUILD_STATUSES
    terminal = (
        workspace.latest_build_transition in {"stop", "delete"}
        or status_value in {"stopped", "failed", "canceled"}
    )
    return active, terminal, workspace.latest_build_id or "-"


async def reserve_public_container(client, owner_username: str, workspace_name: str) -> None:
    """Reserve a slot before Coder creation/start; unknown outcomes stay occupied.

    The independent session is committed before the Coder call, so an API crash
    after accepting admission cannot forget a build that may still be queued.
    A reservation is cleared only after Coder reports a *different* latest
    build. A failed request before build creation requires operator review.
    """
    limit = required_public_container_limit()
    if limit is None:
        return

    identity = (owner_username, workspace_name)
    outcome = "busy"
    try:
        with SessionLocal() as db:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                locked = db.execute(
                    text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": _LOCK_ID}
                ).scalar_one()
                if locked:
                    break
                db.rollback()
                await asyncio.sleep(0.05)
            else:
                raise ServiceUnavailableException(detail="Workspace admission is busy")

            # The Coder method verifies pagination count and refuses an
            # incomplete inventory. Keep this snapshot under the lock.
            workspaces = await client.list_all_workspaces_complete(max_items=_MAX_FLEET_SIZE)
            fleet = {(w.owner_name, w.name): _fleet_record(w) for w in workspaces}
            if len(fleet) != len(workspaces):
                raise ServiceUnavailableException(detail="Workspace fleet inventory is inconsistent")

            rows = db.execute(text(
                "SELECT owner_name, workspace_name, baseline_build_id "
                "FROM public_workspace_reservation"
            )).all()
            reservations = {(row.owner_name, row.workspace_name): row.baseline_build_id for row in rows}
            for key, baseline in list(reservations.items()):
                current = fleet.get(key)
                if current and current[2] != baseline and (current[0] or current[1]):
                    db.execute(text(
                        "DELETE FROM public_workspace_reservation "
                        "WHERE owner_name=:owner AND workspace_name=:workspace"
                    ), {"owner": key[0], "workspace": key[1]})
                    del reservations[key]

            active = sum(record[0] for record in fleet.values())
            target = fleet.get(identity)
            if target and target[0]:
                outcome = "already_active"
            elif identity in reservations:
                outcome = "pending"
            elif active + len(reservations) >= limit:
                outcome = "full"
            else:
                db.execute(text(
                    "INSERT INTO public_workspace_reservation "
                    "(owner_name, workspace_name, baseline_build_id) "
                    "VALUES (:owner, :workspace, :baseline)"
                ), {
                    "owner": owner_username,
                    "workspace": workspace_name,
                    "baseline": target[2] if target else "-",
                })
                outcome = "reserved"
            db.commit()
    except SQLAlchemyError:
        raise ServiceUnavailableException(detail="Workspace admission unavailable") from None

    if outcome in {"reserved", "already_active"}:
        return
    if outcome in {"full", "pending"}:
        from computor_backend.business_logic.instance_limits import _local_install_hint

        detail = (
            f"Hosted workspaces are at capacity ({limit} running or starting)."
            if outcome == "full" else "This workspace is already starting."
        )
        raise RateLimitException(
            error_code="WORKSPACE_CAPACITY",
            detail=detail + _local_install_hint(),
            retry_after=60,
        )
    raise ServiceUnavailableException(detail="Workspace admission unavailable")
