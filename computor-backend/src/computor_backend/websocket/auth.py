"""
WebSocket authentication module.

Provides authentication for WebSocket connections using Bearer tokens.
Supports both:
1. SSO session tokens (stored in Redis)
2. API tokens (ctp_* prefix, stored in database)
"""

import json
import logging
from typing import Optional

from fastapi import WebSocket, WebSocketException, status

from computor_backend.database import get_db
from computor_backend.model.role import UserRole
from computor_backend.permissions.auth import (
    AuthenticationResult,
    AuthenticationService,
    PrincipalBuilder,
    SSO_SESSION_TTL,
)
from computor_backend.permissions.principal import Principal
from computor_backend.redis_cache import get_redis_client
from computor_backend.utils.token_hash import hash_token
from computor_backend.utils.api_token import validate_token_format

logger = logging.getLogger(__name__)


class WebSocketAuthError(Exception):
    """Exception raised when WebSocket authentication fails."""

    def __init__(self, code: int, reason: str):
        self.code = code
        self.reason = reason
        super().__init__(reason)


async def authenticate_websocket_token(token: str) -> Principal:
    """
    Authenticate a WebSocket connection using a token.

    Supports two authentication methods:
    1. API tokens (ctp_* prefix) - looked up in database
    2. SSO session tokens - looked up in Redis

    Args:
        token: Token from query parameter

    Returns:
        Principal object with user info and permissions

    Raises:
        WebSocketAuthError: If authentication fails
    """
    if not token:
        raise WebSocketAuthError(4001, "No token provided")

    # Check if this is an API token (ctp_* prefix)
    if validate_token_format(token):
        return await _authenticate_api_token(token)

    # Otherwise try SSO session token
    return await _authenticate_sso_token(token)


async def _authenticate_api_token(token: str) -> Principal:
    """
    Authenticate using API token (ctp_* prefix).

    Args:
        token: API token string

    Returns:
        Principal object

    Raises:
        WebSocketAuthError: If authentication fails
    """
    try:
        with next(get_db()) as db:
            auth_result = AuthenticationService.authenticate_api_token(token, db)
            principal = PrincipalBuilder.build(auth_result, db)

        logger.info(f"WebSocket API token authentication successful for user {principal.user_id}")
        return principal

    except Exception as e:
        logger.warning(f"WebSocket API token auth failed: {e}")
        raise WebSocketAuthError(4001, "Invalid or expired API token")


async def _authenticate_sso_token(token: str) -> Principal:
    """
    Authenticate using SSO session token (stored in Redis).

    Args:
        token: SSO session token

    Returns:
        Principal object

    Raises:
        WebSocketAuthError: If authentication fails
    """
    redis_client = await get_redis_client()

    # Hash token for lookup (same as SSO auth)
    token_hash = hash_token(token)
    session_key = f"sso_session:{token_hash}"

    # Look up session
    session_data_raw = await redis_client.get(session_key)

    if not session_data_raw:
        logger.warning(f"WebSocket auth failed: session not found for token hash {token_hash[:8]}...")
        raise WebSocketAuthError(4001, "Invalid or expired token")

    try:
        session_data = json.loads(session_data_raw)
        user_id = session_data.get("user_id")
        provider = session_data.get("provider", "sso")

        if not user_id:
            raise WebSocketAuthError(4001, "Invalid session data")

        # Get user roles from database
        with next(get_db()) as db:
            results = (
                db.query(UserRole.role_id)
                .filter(UserRole.user_id == user_id)
                .all()
            )
            role_ids = [r[0] for r in results if r[0] is not None]

            # Build authentication result
            auth_result = AuthenticationResult(user_id, role_ids, provider)

            # Build Principal with full claims
            principal = PrincipalBuilder.build(auth_result, db)

        # Refresh session TTL
        await redis_client.expire(session_key, SSO_SESSION_TTL)

        logger.info(f"WebSocket SSO authentication successful for user {user_id}")
        return principal

    except json.JSONDecodeError:
        logger.error("WebSocket auth failed: invalid session data format")
        raise WebSocketAuthError(4001, "Invalid session data")
    except WebSocketAuthError:
        raise
    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}")
        raise WebSocketAuthError(4001, "Authentication failed")


async def get_websocket_principal(websocket: WebSocket, token: Optional[str] = None) -> Principal:
    """
    FastAPI dependency for WebSocket authentication.

    Extracts token from query parameter and authenticates.

    Args:
        websocket: The WebSocket connection
        token: Token from query parameter (injected by FastAPI)

    Returns:
        Authenticated Principal

    Raises:
        WebSocketException: If authentication fails (closes connection with 4001)
    """
    if not token:
        # Try to get from query params
        token = websocket.query_params.get("token")

    if not token:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="No token provided")

    try:
        return await authenticate_websocket_token(token)
    except WebSocketAuthError as e:
        raise WebSocketException(code=e.code, reason=e.reason)
