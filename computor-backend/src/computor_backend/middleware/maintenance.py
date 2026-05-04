"""
Maintenance mode middleware.

Uses pure ASGI instead of BaseHTTPMiddleware to properly support WebSocket connections.
When maintenance mode is active, blocks mutating requests (POST/PUT/PATCH/DELETE)
while allowing GET/HEAD/OPTIONS requests for read-only access.

Admin users are NOT blocked - their requests pass through during maintenance.
"""

import hashlib
import json
import logging
import time
from typing import Optional, Tuple

from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

REDIS_KEY_STATE = "maintenance:state"
REDIS_KEY_SCHEDULE = "maintenance:schedule"

# Paths that are ALWAYS allowed regardless of maintenance mode
EXEMPT_PATH_PREFIXES = (
    "/auth/",
    "/password/",
    "/ws",
    "/system/maintenance",
)

EXEMPT_PATHS_EXACT = (
    "/",
)

# Read-only HTTP methods that pass through during maintenance
READONLY_METHODS = ("GET", "HEAD", "OPTIONS")


class MaintenanceMiddleware:
    """
    Pure ASGI middleware that enforces maintenance mode.

    When maintenance mode is active:
    - GET/HEAD/OPTIONS requests pass through (read-only access)
    - Admin users pass through regardless of method
    - POST/PUT/PATCH/DELETE from non-admins return 503
    - Exempt paths (auth, ws, maintenance admin) always pass through
    - WebSocket connections are NOT blocked (they receive notifications instead)

    Uses in-memory cache with 2-second TTL to avoid Redis calls on every request.
    Falls back to "not in maintenance" if Redis is unavailable.
    """

    def __init__(self, app: ASGIApp, cache_ttl: float = 2.0):
        self.app = app
        self.cache_ttl = cache_ttl
        self._cached_active: bool = False
        self._cached_message: str = ""
        self._cache_expires_at: float = 0.0

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        # Pass through non-HTTP requests (WebSocket, lifespan, etc.)
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "GET")

        # Check if path is exempt
        if self._is_exempt(path):
            await self.app(scope, receive, send)
            return

        # Read-only methods always pass through
        if method in READONLY_METHODS:
            await self.app(scope, receive, send)
            return

        # Check maintenance state (cached)
        is_active, message = await self._get_maintenance_state()

        if not is_active:
            await self.app(scope, receive, send)
            return

        # Maintenance is active - check if the request is from an admin
        if await self._is_admin_request(scope):
            await self.app(scope, receive, send)
            return

        # Block mutating request from non-admin
        logger.info(f"Maintenance mode: blocked {method} {path}")

        response = JSONResponse(
            status_code=503,
            content={
                "error_code": "MAINT_001",
                "detail": "Service is under maintenance",
                "message": message or "The system is currently under maintenance. Read-only access is available.",
                "maintenance": True,
            },
            headers={
                "Retry-After": "300",
            },
        )
        await response(scope, receive, send)

    def _is_exempt(self, path: str) -> bool:
        """Check if path is exempt from maintenance blocking."""
        if path in EXEMPT_PATHS_EXACT:
            return True
        for prefix in EXEMPT_PATH_PREFIXES:
            if path.startswith(prefix):
                return True
        return False

    async def _get_maintenance_state(self) -> Tuple[bool, str]:
        """
        Get maintenance state with in-memory caching.

        Returns (is_active, message).
        Falls back to (False, "") if Redis is unavailable.
        """
        now = time.monotonic()
        if now < self._cache_expires_at:
            return self._cached_active, self._cached_message

        try:
            from computor_backend.redis_cache import get_redis_client

            redis = await get_redis_client()
            state = await redis.hgetall(REDIS_KEY_STATE)

            if state:
                self._cached_active = state.get("active") == "1"
                self._cached_message = state.get("message", "")
            else:
                self._cached_active = False
                self._cached_message = ""

            self._cache_expires_at = now + self.cache_ttl

        except Exception as e:
            logger.warning(f"Failed to check maintenance state from Redis: {e}")
            # Fail-open: if Redis is down, don't block requests
            self._cached_active = False
            self._cached_message = ""
            self._cache_expires_at = now + 0.5

        return self._cached_active, self._cached_message

    async def _is_admin_request(self, scope: Scope) -> bool:
        """
        Best-effort check if the request is from an admin user.

        Reuses the existing Principal cache in Redis (written by the auth system).
        Single Redis GET per check - no DB access needed.

        Returns False on any failure (admin should have a cached session).
        """
        headers = dict(scope.get("headers", []))

        # Try Bearer token from Authorization header
        auth_header = headers.get(b"authorization", b"")
        if isinstance(auth_header, bytes):
            auth_header = auth_header.decode("utf-8", errors="ignore")

        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
            if token and await self._check_principal_cache("sso_permissions", token):
                return True

        # Try API token from X-API-Token header
        api_token = headers.get(b"x-api-token", b"")
        if isinstance(api_token, bytes):
            api_token = api_token.decode("utf-8", errors="ignore")

        if api_token:
            if await self._check_principal_cache("api_token_permissions", api_token):
                return True

        # Try cookie ct_access_token
        cookie_header = headers.get(b"cookie", b"")
        if isinstance(cookie_header, bytes):
            cookie_header = cookie_header.decode("utf-8", errors="ignore")

        if cookie_header:
            token = self._extract_cookie(cookie_header, "ct_access_token")
            if token and await self._check_principal_cache("sso_permissions", token):
                return True

        return False

    async def _check_principal_cache(self, prefix: str, token: str) -> bool:
        """
        Check if a cached Principal indicates admin status.

        Uses the same cache key format as permissions/auth.py:
            sha256(f"{prefix}:{token}").hexdigest()
        """
        try:
            from computor_backend.redis_cache import get_redis_client

            cache_key = hashlib.sha256(f"{prefix}:{token}".encode()).hexdigest()
            redis = await get_redis_client()
            cached_data = await redis.get(cache_key)

            if cached_data:
                principal_data = json.loads(cached_data)
                return principal_data.get("is_admin", False)
        except Exception:
            # Cache lookup failed — fall through and treat as non-admin to keep
            # the maintenance gate strict. Logged at debug to avoid spamming on
            # cache outages.
            logger.debug("Maintenance admin cache lookup failed", exc_info=True)

        return False

    @staticmethod
    def _extract_cookie(cookie_header: str, name: str) -> Optional[str]:
        """Extract a cookie value from the Cookie header string."""
        for part in cookie_header.split(";"):
            part = part.strip()
            if part.startswith(f"{name}="):
                return part[len(name) + 1:]
        return None
