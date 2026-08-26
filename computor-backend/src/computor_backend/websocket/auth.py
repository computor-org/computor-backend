"""
WebSocket authentication module.

Provides authentication for WebSocket connections using Bearer tokens.
Supports both:
1. SSO session tokens (stored in Redis)
2. API tokens (ctp_* prefix, stored in database)

Authentication does not stop at the handshake (issue #257). Before, a socket
authenticated once and was never revisited, so a connection happily outlived
the credential that opened it: HTTP started answering 401 while the socket sat
there looking healthy, and the client only learned its session was gone from
the next failed request. The handshake now also resolves *when* that credential
dies (:class:`WebSocketCredential`), and the endpoint watches that deadline —
see ``router._watch_credential_expiry``.
"""

import datetime
import json
import logging
from dataclasses import dataclass
from typing import Optional, Tuple

from fastapi import WebSocket, WebSocketException, status

from computor_backend.database import get_db_session
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
from computor_backend.utils.api_token import hash_api_token, validate_token_format

logger = logging.getLogger(__name__)

#: Handshake rejected the credential outright.
WS_CLOSE_AUTH_FAILED = 4001

#: The credential that opened this connection has since expired. Deliberately
#: distinct from 4001: 4001 means "your token was never good", 4003 means "it
#: was, and now it is not" — the first needs a new credential from the user,
#: the second is usually fixed by a silent refresh, so clients must be able to
#: tell them apart without parsing a reason string.
WS_CLOSE_TOKEN_EXPIRED = 4003


class WebSocketAuthError(Exception):
    """Exception raised when WebSocket authentication fails."""

    def __init__(self, code: int, reason: str):
        self.code = code
        self.reason = reason
        super().__init__(reason)


@dataclass
class WebSocketCredential:
    """
    What authenticated a connection, and when it stops being valid.

    Deliberately holds no raw token — a long-lived connection record is the
    last place a credential should be sitting. ``session_key`` is already a
    hash-derived Redis key, which is enough to re-read the SSO TTL.
    """

    #: ``"api_token"`` or ``"sso"`` — which branch authenticated.
    kind: str
    #: When the credential expires; ``None`` when it never does.
    expires_at: Optional[datetime.datetime] = None
    #: Redis key of the SSO session, for re-reading its sliding TTL. None for API tokens.
    session_key: Optional[str] = None


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


async def authenticate_websocket_token(token: str) -> Tuple[Principal, WebSocketCredential]:
    """
    Authenticate a WebSocket connection using a token.

    Supports two authentication methods:
    1. API tokens (ctp_* prefix) - looked up in database
    2. SSO session tokens - looked up in Redis

    Args:
        token: Token from query parameter

    Returns:
        The authenticated Principal and the credential's expiry information.

    Raises:
        WebSocketAuthError: If authentication fails
    """
    if not token:
        raise WebSocketAuthError(WS_CLOSE_AUTH_FAILED, "No token provided")

    # Check if this is an API token (ctp_* prefix)
    if validate_token_format(token):
        return await _authenticate_api_token(token)

    # Otherwise try SSO session token
    return await _authenticate_sso_token(token)


async def _authenticate_api_token(token: str) -> Tuple[Principal, WebSocketCredential]:
    """
    Authenticate using API token (ctp_* prefix).

    Args:
        token: API token string

    Returns:
        The authenticated Principal and the token's expiry (``None`` for a
        token minted without one).

    Raises:
        WebSocketAuthError: If authentication fails
    """
    try:
        with get_db_session() as db:
            auth_result = await AuthenticationService.authenticate_api_token(token, db)
            principal = PrincipalBuilder.build(auth_result, db)

        expires_at = await _api_token_expiry(token)

        logger.info(f"WebSocket API token authentication successful for user {principal.user_id}")
        return principal, WebSocketCredential(kind="api_token", expires_at=expires_at)

    except Exception as e:
        logger.warning(f"WebSocket API token auth failed: {e}")
        raise WebSocketAuthError(WS_CLOSE_AUTH_FAILED, "Invalid or expired API token")


async def _api_token_expiry(token: str) -> Optional[datetime.datetime]:
    """
    Read an authenticated API token's ``expires_at`` from the token cache.

    ``authenticate_api_token`` populates that cache on every path it returns
    successfully from (hit or miss), so this is a Redis read rather than a
    second database round-trip. A cache entry that has since fallen out under
    us just means "no deadline known" — the connection stays open and the next
    HTTP call still enforces expiry, which is the pre-#257 behaviour and never
    worse than it.
    """
    from computor_backend.permissions.api_token_cache import get_cached_token_data

    try:
        cached = await get_cached_token_data(hash_api_token(token).hex())
    except Exception as e:  # pragma: no cover - cache outage
        logger.warning(f"Could not resolve API token expiry, leaving connection unwatched: {e}")
        return None

    if not cached or not cached.expires_at:
        return None

    try:
        expires_at = datetime.datetime.fromisoformat(cached.expires_at)
    except ValueError:
        logger.warning(f"Unparseable API token expiry {cached.expires_at!r}, leaving connection unwatched")
        return None

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)
    return expires_at


async def _authenticate_sso_token(token: str) -> Tuple[Principal, WebSocketCredential]:
    """
    Authenticate using SSO session token (stored in Redis).

    Args:
        token: SSO session token

    Returns:
        The authenticated Principal and the session's expiry, taken from the
        Redis key's own TTL rather than assumed to be a full ``SSO_SESSION_TTL``
        from now — the socket may well be opening against a session that is
        most of the way through its life.

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
        raise WebSocketAuthError(WS_CLOSE_AUTH_FAILED, "Invalid or expired token")

    try:
        session_data = json.loads(session_data_raw)
        user_id = session_data.get("user_id")
        provider = session_data.get("provider", "sso")

        if not user_id:
            raise WebSocketAuthError(WS_CLOSE_AUTH_FAILED, "Invalid session data")

        # Get user roles from database
        with get_db_session() as db:
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

        # Refresh session TTL — the handshake is user activity like any other
        # request. The watchdog that later re-reads this TTL deliberately does
        # NOT refresh it, or a connection would keep its own session alive
        # forever and expiry would never arrive.
        await redis_client.expire(session_key, SSO_SESSION_TTL)

        logger.info(f"WebSocket SSO authentication successful for user {user_id}")
        credential = WebSocketCredential(
            kind="sso",
            expires_at=_utcnow() + datetime.timedelta(seconds=SSO_SESSION_TTL),
            session_key=session_key,
        )
        return principal, credential

    except json.JSONDecodeError:
        logger.error("WebSocket auth failed: invalid session data format")
        raise WebSocketAuthError(WS_CLOSE_AUTH_FAILED, "Invalid session data")
    except WebSocketAuthError:
        raise
    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}")
        raise WebSocketAuthError(WS_CLOSE_AUTH_FAILED, "Authentication failed")


async def current_credential_expiry(
    credential: WebSocketCredential,
) -> Optional[datetime.datetime]:
    """
    Re-resolve when a live connection's credential dies.

    SSO sessions slide: every authenticated HTTP request pushes the Redis key's
    TTL back out, so the deadline captured at handshake is a floor, not a fact.
    Re-reading the TTL is what lets an actively-working user keep a socket for
    hours while an idle one still closes on time. The read is deliberately
    non-refreshing (``ttl``, never ``expire``).

    API tokens carry a fixed ``expires_at``, so their deadline is simply the one
    resolved at handshake.

    Returns:
        The current deadline, or ``None`` when the credential has no expiry and
        there is nothing left to watch.

    Raises:
        WebSocketAuthError: with :data:`WS_CLOSE_TOKEN_EXPIRED` when the
            credential is already gone — an SSO session that expired or was
            signed out from elsewhere.
    """
    if credential.kind != "sso" or not credential.session_key:
        return credential.expires_at

    redis_client = await get_redis_client()
    ttl = await redis_client.ttl(credential.session_key)

    # redis-py mirrors the Redis contract: -2 = no such key, -1 = key without
    # a TTL. Only the first means the session ended.
    if ttl == -2:
        raise WebSocketAuthError(WS_CLOSE_TOKEN_EXPIRED, "Session expired")
    if ttl is None or ttl < 0:
        return None

    return _utcnow() + datetime.timedelta(seconds=ttl)


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
        principal, _credential = await authenticate_websocket_token(token)
        return principal
    except WebSocketAuthError as e:
        raise WebSocketException(code=e.code, reason=e.reason)
