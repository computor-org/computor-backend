"""Session management API endpoints."""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

from computor_backend.database import get_db
from computor_backend.redis_cache import get_redis_client
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.repositories.session_repo import SessionRepository
from computor_backend.model.auth import Session as SessionModel
from computor_backend.api.exceptions import NotFoundException, UnauthorizedException
from computor_backend.utils.token_hash import hash_token
from computor_types.sessions import SessionList, SessionGet

session_router = APIRouter(prefix="/sessions", tags=["sessions"])


# ============================================================================
# USER-LEVEL ENDPOINTS - Manage own sessions
# ============================================================================

@session_router.get("/me", response_model=List[SessionList])
async def list_my_sessions(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    cache = Depends(get_redis_client),
):
    """
    List all active sessions for the authenticated user.
    
    Returns sessions ordered by last activity (most recent first).
    """
    session_repo = SessionRepository(db, cache)
    sessions = session_repo.find_active_sessions_by_user(principal.user_id)
    return [SessionList.model_validate(s, from_attributes=True) for s in sessions]


@session_router.get("/me/current", response_model=SessionGet)
async def get_current_session(
    request: Request,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    cache = Depends(get_redis_client),
):
    """Get details of the current session (based on access token)."""
    # Extract token from Authorization header
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise UnauthorizedException("No valid token provided")

    token = authorization.replace("Bearer ", "")
    token_hash = hash_token(token)

    session_repo = SessionRepository(db, cache)
    session = session_repo.find_by_session_id_hash(token_hash)

    if not session:
        raise NotFoundException("Current session not found")

    # Verify session belongs to authenticated user
    if str(session.user_id) != str(principal.user_id):
        raise UnauthorizedException("Session does not belong to authenticated user")

    return SessionGet.model_validate(session, from_attributes=True)


@session_router.delete("/me/{session_id}")
async def revoke_my_session(
    session_id: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    cache = Depends(get_redis_client),
):
    """
    Revoke a specific session (remote logout).
    
    Use this to logout from another device remotely.
    """
    from computor_backend.redis_cache import get_redis_client

    session_repo = SessionRepository(db, cache)
    session = session_repo.get(session_id)

    if not session:
        raise NotFoundException("Session not found")

    # CRITICAL: Verify session belongs to user
    if str(session.user_id) != str(principal.user_id):
        raise UnauthorizedException("Cannot revoke another user's session")

    # Revoke in database
    session_repo.revoke_session(session_id, reason="User revoked via API")

    # Delete from Redis cache
    redis_client = await get_redis_client()
    await redis_client.delete(f"sso_session:{session.session_id}")

    return {"message": "Session revoked successfully", "session_id": session_id}


@session_router.delete("/me/all")
async def revoke_all_my_sessions(
    request: Request,
    include_current: bool = Query(False, description="Also revoke current session"),
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    cache = Depends(get_redis_client),
):
    """
    Revoke all sessions for the current user.
    
    By default, keeps the current session active. Set include_current=true to logout everywhere.
    """
    from computor_backend.redis_cache import get_redis_client

    # Determine current session to optionally exclude
    current_session_id = None
    if not include_current:
        authorization = request.headers.get("Authorization", "")
        if authorization.startswith("Bearer "):
            token = authorization.replace("Bearer ", "")
            token_hash = hash_token(token)
            session_repo = SessionRepository(db, cache)
            current_session = session_repo.find_by_session_id_hash(token_hash)
            if current_session:
                current_session_id = str(current_session.id)

    # Revoke all sessions
    session_repo = SessionRepository(db, cache)
    count = session_repo.revoke_all_user_sessions(
        user_id=principal.user_id,
        reason="User requested logout from all devices",
        exclude_session_id=current_session_id
    )

    # Clean up Redis
    redis_client = await get_redis_client()
    sessions = session_repo.find_active_sessions_by_user(principal.user_id)
    for session in sessions:
        if current_session_id and str(session.id) == current_session_id:
            continue
        await redis_client.delete(f"sso_session:{session.session_id}")

    return {
        "message": f"Revoked {count} session(s)",
        "count": count,
        "current_session_kept": not include_current
    }


# ============================================================================
# ADMIN-LEVEL ENDPOINTS - Manage any user's sessions
# ============================================================================

@session_router.get("/admin/users/{user_id}", response_model=List[SessionGet])
async def list_user_sessions_admin(
    user_id: str,
    active_only: bool = Query(True, description="Only show active sessions"),
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    cache = Depends(get_redis_client),
):
    """List sessions for any user (admin only)."""
    # Check admin permission
    if "_admin" not in principal.roles and "_maintainer" not in principal.roles:
        raise UnauthorizedException("Admin or maintainer access required")

    session_repo = SessionRepository(db, cache)

    if active_only:
        sessions = session_repo.find_active_sessions_by_user(user_id)
    else:
        # Query all sessions including ended ones
        sessions = db.query(SessionModel).filter(
            SessionModel.user_id == user_id
        ).order_by(SessionModel.created_at.desc()).all()

    return [SessionGet.model_validate(s, from_attributes=True) for s in sessions]


@session_router.delete("/admin/{session_id}")
async def revoke_session_admin(
    session_id: str,
    reason: str = Query("Admin revoked", description="Reason for revocation"),
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    cache = Depends(get_redis_client),
):
    """Force revoke any session (admin only)."""
    import logging

    # Check admin permission
    if "_admin" not in principal.roles and "_maintainer" not in principal.roles:
        raise UnauthorizedException("Admin or maintainer access required")

    session_repo = SessionRepository(db, cache)
    session = session_repo.get(session_id)

    if not session:
        raise NotFoundException("Session not found")

    # Revoke with admin reason
    session_repo.revoke_session(
        session_id,
        reason=f"Admin revoked: {reason} (by {principal.user_id})"
    )

    # Clean up Redis
    redis_client = await get_redis_client()
    await redis_client.delete(f"sso_session:{session.session_id}")

    logger = logging.getLogger(__name__)
    logger.warning(f"Admin {principal.user_id} revoked session {session_id} for user {session.user_id}")

    return {
        "message": "Session revoked by admin",
        "session_id": session_id,
        "affected_user_id": str(session.user_id)
    }


@session_router.delete("/admin/users/{user_id}/all")
async def revoke_all_user_sessions_admin(
    user_id: str,
    reason: str = Query("Admin action", description="Reason for mass revocation"),
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    cache = Depends(get_redis_client),
):
    """Revoke all sessions for a user (admin only)."""
    import logging

    # Check admin permission
    if "_admin" not in principal.roles and "_maintainer" not in principal.roles:
        raise UnauthorizedException("Admin or maintainer access required")

    session_repo = SessionRepository(db, cache)
    count = session_repo.revoke_all_user_sessions(
        user_id=user_id,
        reason=f"Admin action: {reason} (by {principal.user_id})"
    )

    # Clean up Redis
    redis_client = await get_redis_client()
    sessions = db.query(SessionModel).filter(SessionModel.user_id == user_id).all()
    for session in sessions:
        await redis_client.delete(f"sso_session:{session.session_id}")

    logger = logging.getLogger(__name__)
    logger.warning(f"Admin {principal.user_id} revoked {count} sessions for user {user_id}")

    return {
        "message": f"Revoked {count} session(s)",
        "count": count,
        "affected_user_id": user_id
    }


@session_router.get("/admin/stats")
async def get_session_stats(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    """Get session statistics (admin only)."""
    if "_admin" not in principal.roles:
        raise UnauthorizedException("Admin access required")

    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    
    # Active sessions
    active_count = db.query(func.count(SessionModel.id)).filter(
        SessionModel.revoked_at.is_(None),
        SessionModel.ended_at.is_(None)
    ).scalar()

    # Sessions created in last 24 hours
    yesterday = now - timedelta(days=1)
    recent_count = db.query(func.count(SessionModel.id)).filter(
        SessionModel.created_at >= yesterday
    ).scalar()

    # Unique active users
    active_users = db.query(func.count(func.distinct(SessionModel.user_id))).filter(
        SessionModel.revoked_at.is_(None),
        SessionModel.ended_at.is_(None)
    ).scalar()

    # Total sessions (all time)
    total_sessions = db.query(func.count(SessionModel.id)).scalar()

    return {
        "active_sessions": active_count,
        "active_users": active_users,
        "sessions_last_24h": recent_count,
        "total_sessions_all_time": total_sessions,
        "timestamp": now.isoformat()
    }
