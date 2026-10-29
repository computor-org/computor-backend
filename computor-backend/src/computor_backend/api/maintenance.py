"""
Maintenance mode API endpoints.

Allows admins to schedule, activate, deactivate maintenance mode
and query current maintenance status.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Annotated, Dict, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from computor_backend.database import get_db
from computor_backend.model.auth import User
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.core import check_admin
from computor_backend.permissions.principal import Principal
from computor_backend.exceptions import ForbiddenException, BadRequestException
from computor_backend.redis_cache import get_redis_client
from computor_types.maintenance import (
    DEFAULT_TEXTS,
    MaintenanceActivate,
    MaintenanceSchedule,
    MaintenanceStatusGet,
    stored_message_i18n,
)

logger = logging.getLogger(__name__)

maintenance_router = APIRouter()

REDIS_KEY_STATE = "maintenance:state"
REDIS_KEY_SCHEDULE = "maintenance:schedule"


def request_message_i18n(request, default_key: str) -> Optional[Dict[str, str]]:
    """Both languages for a request: its own pair, the built-in pair when the
    admin wrote no message, else none (free text is in one language only)."""
    if request.message_i18n:
        return request.message_i18n
    if "message" not in request.model_fields_set:
        return dict(DEFAULT_TEXTS[default_key])
    return None


def _with_i18n(data: dict, message_i18n: Optional[Dict[str, str]]) -> dict:
    if message_i18n:
        data["message_i18n"] = message_i18n
    return data


# --- Endpoints ---


@maintenance_router.get("/status", response_model=MaintenanceStatusGet)
async def get_maintenance_status(
    permissions: Annotated[Principal, Depends(get_current_principal)],
):
    """
    Get current maintenance status.

    Available to all authenticated users.
    Returns both active maintenance state and any scheduled maintenance.
    """
    redis = await get_redis_client()

    state = await redis.hgetall(REDIS_KEY_STATE)
    schedule = await redis.hgetall(REDIS_KEY_SCHEDULE)

    return MaintenanceStatusGet(
        active=state.get("active") == "1" if state else False,
        message=state.get("message", "") if state else "",
        message_i18n=stored_message_i18n(state.get("message_i18n")) if state else None,
        activated_at=state.get("activated_at") if state else None,
        activated_by=state.get("activated_by") if state else None,
        activated_by_name=state.get("activated_by_name") if state else None,
        scheduled_at=schedule.get("scheduled_at") if schedule else None,
        scheduled_by=schedule.get("scheduled_by") if schedule else None,
        scheduled_by_name=schedule.get("scheduled_by_name") if schedule else None,
    )


@maintenance_router.post("/activate")
async def activate_maintenance(
    request: MaintenanceActivate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db, scope="function"),
):
    """
    Activate maintenance mode immediately.

    Admin only. Blocks all mutating requests (POST/PUT/PATCH/DELETE) for non-admin users.
    GET requests, auth endpoints, and admin requests remain accessible.
    """
    if not check_admin(permissions):
        raise ForbiddenException(detail="Admin privileges required")

    redis = await get_redis_client()
    now = datetime.now(timezone.utc).isoformat()

    # Look up user display name
    user = db.query(User).filter(User.id == permissions.user_id).first()
    display_name = f"{user.given_name} {user.family_name}" if user and user.given_name else permissions.user_id

    message_i18n = request_message_i18n(request, "activated")
    await redis.delete(REDIS_KEY_STATE)
    await redis.hset(REDIS_KEY_STATE, mapping={
        "active": "1",
        "message": request.message,
        "activated_at": now,
        "activated_by": permissions.user_id,
        "activated_by_name": display_name,
        **({"message_i18n": json.dumps(message_i18n)} if message_i18n else {}),
    })

    # Clear any schedule since we're activating now
    await redis.delete(REDIS_KEY_SCHEDULE)

    logger.warning(f"Maintenance mode ACTIVATED by {permissions.user_id}: {request.message}")

    if request.notify_websocket:
        await _broadcast_maintenance_event("maintenance:activated", _with_i18n({
            "active": True,
            "message": request.message,
            "activated_at": now,
        }, message_i18n))

    return {
        "status": "activated",
        "message": request.message,
        "activated_at": now,
    }


@maintenance_router.post("/deactivate")
async def deactivate_maintenance(
    permissions: Annotated[Principal, Depends(get_current_principal)],
):
    """
    Deactivate maintenance mode.

    Admin only. Immediately restores full service for all users.
    """
    if not check_admin(permissions):
        raise ForbiddenException(detail="Admin privileges required")

    redis = await get_redis_client()

    await redis.delete(REDIS_KEY_STATE)
    await redis.delete(REDIS_KEY_SCHEDULE)

    logger.warning(f"Maintenance mode DEACTIVATED by {permissions.user_id}")

    await _broadcast_maintenance_event("maintenance:deactivated", {
        "active": False,
        "message": DEFAULT_TEXTS["deactivated"]["en"],
        "message_i18n": dict(DEFAULT_TEXTS["deactivated"]),
    })

    return {"status": "deactivated"}


@maintenance_router.post("/schedule")
async def schedule_maintenance(
    request: MaintenanceSchedule,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db, scope="function"),
):
    """
    Schedule future maintenance.

    Admin only. Sets a scheduled time and optionally notifies connected users.
    Does NOT activate maintenance mode -- that requires a separate activate call
    or can be triggered by ``computor.sh maintenance enter``.
    """
    if not check_admin(permissions):
        raise ForbiddenException(detail="Admin privileges required")

    # Validate datetime — replace trailing 'Z' with '+00:00' for Python < 3.11 compat
    try:
        raw = request.scheduled_at.replace("Z", "+00:00")
        scheduled_dt = datetime.fromisoformat(raw)
    except ValueError:
        raise BadRequestException(detail="Invalid datetime format. Use ISO8601.")

    if scheduled_dt.tzinfo is None:
        scheduled_dt = scheduled_dt.replace(tzinfo=timezone.utc)

    if scheduled_dt <= datetime.now(timezone.utc):
        raise BadRequestException(detail="Scheduled time must be in the future")

    redis = await get_redis_client()
    now = datetime.now(timezone.utc).isoformat()

    # Look up user display name
    user = db.query(User).filter(User.id == permissions.user_id).first()
    display_name = f"{user.given_name} {user.family_name}" if user and user.given_name else permissions.user_id

    message_i18n = request_message_i18n(request, "scheduled")
    await redis.delete(REDIS_KEY_SCHEDULE)
    await redis.hset(REDIS_KEY_SCHEDULE, mapping={
        "scheduled_at": request.scheduled_at,
        "message": request.message,
        "scheduled_by": permissions.user_id,
        "scheduled_by_name": display_name,
        "created_at": now,
        **({"message_i18n": json.dumps(message_i18n)} if message_i18n else {}),
    })

    logger.info(f"Maintenance SCHEDULED for {request.scheduled_at} by {permissions.user_id}")

    if request.notify_websocket:
        await _broadcast_maintenance_event("maintenance:scheduled", _with_i18n({
            "scheduled_at": request.scheduled_at,
            "message": request.message,
        }, message_i18n))

    return {
        "status": "scheduled",
        "scheduled_at": request.scheduled_at,
        "message": request.message,
    }


@maintenance_router.delete("/schedule")
async def cancel_scheduled_maintenance(
    permissions: Annotated[Principal, Depends(get_current_principal)],
):
    """Cancel scheduled maintenance."""
    if not check_admin(permissions):
        raise ForbiddenException(detail="Admin privileges required")

    redis = await get_redis_client()
    await redis.delete(REDIS_KEY_SCHEDULE)

    logger.info(f"Scheduled maintenance CANCELLED by {permissions.user_id}")

    await _broadcast_maintenance_event("maintenance:cancelled", {
        "message": DEFAULT_TEXTS["cancelled"]["en"],
        "message_i18n": dict(DEFAULT_TEXTS["cancelled"]),
    })

    return {"status": "cancelled"}


async def _broadcast_maintenance_event(event_type: str, data: dict):
    """
    Broadcast a maintenance event to all connected WebSocket users
    via Redis pub/sub (supports multi-instance deployments).
    """
    try:
        from computor_backend.websocket.pubsub import pubsub

        await pubsub.publish("system:maintenance", event_type, data)
    except Exception as e:
        logger.error(f"Failed to broadcast maintenance event: {e}")
