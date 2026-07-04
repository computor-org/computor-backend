"""
GDPR consent-gate middleware.

Blocks API access for AUTHENTICATED users who have not consented to the
current privacy-policy version. Unauthenticated requests pass through — the
per-route auth dependency handles them (no double-handling).

Pure ASGI (not BaseHTTPMiddleware) to keep WebSocket upgrades working, same
as the other middlewares in this package.

REGISTRATION ORDER (server.py): authentication in this codebase is a per-route
dependency, not middleware, so the request has no resolved Principal when any
middleware runs. This gate therefore resolves the user itself via
middleware/principal_lookup.py (Redis principal cache, sso_session fallback,
api_token DB fallback). The gate must be added so it runs INSIDE CORS (so 403
responses carry CORS headers) — see the middleware block in server.py.

Gate logic per request:
  1. Non-HTTP scope (WebSocket, lifespan) -> pass.
  2. OPTIONS (CORS preflight) or whitelisted path -> pass.
  3. Resolve the principal (see principal_lookup docstring for precedence and
     sources). Unresolvable -> pass (the route's auth dependency will 401;
     note HTTP Basic is not resolvable here and is therefore not gated).
  4. Service principals (is_service) -> pass; automation is not a data subject
     giving consent.
  5. Resolve the current policy version via the same Redis-cached helper the
     consent endpoints use (business_logic.consent.resolve_current_policy_version),
     so gate and API always agree on the required version. No version
     configured -> gate inactive, pass.
  6. Check consent (Redis `consent:{user_id}:{version}`, DB fallback).
  7. No valid consent -> 403 {"error": "consent_required", "required_version": ...}.

Fail-open: on Redis/DB errors the request passes (logged). Consistent with
MaintenanceMiddleware — an infrastructure outage must not take down the API.
The downstream app is always invoked OUTSIDE the check's try block so
endpoint exceptions propagate normally and are never swallowed or retried.
"""

import logging
from typing import Optional

from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from computor_backend.middleware.principal_lookup import resolve_principal_from_scope

logger = logging.getLogger(__name__)

# Paths reachable WITHOUT consent. Prefixes end with "/" so they cannot
# accidentally cover sibling routes (e.g. "/docs" must not exempt "/documents",
# "/ws" would exempt "/workspaces/..."; WebSockets are already skipped by
# scope type).
EXEMPT_PATHS_EXACT = (
    "/",                   # HEAD / liveness probe
    "/consent",            # POST /consent (the consent endpoints themselves)
    "/docs",               # Swagger UI
    "/redoc",
    "/openapi.json",
    "/extensions-public",
    "/extensions-getting-started",
)

EXEMPT_PATH_PREFIXES = (
    "/consent/",           # status / policy / withdraw / policy-versions
    "/auth/",              # login / logout / callback / token refresh
    "/password/",          # password reset flow
    "/invites/",           # public invite acceptance (pre-account)
    "/docs/",              # Swagger UI sub-paths (oauth2-redirect)
)

# GET-only exemptions: the web UI must be able to load the signed-in user's
# identity to render the consent page itself. Exact paths, so /user-roles etc.
# stay gated.
EXEMPT_GET_PATHS_EXACT = (
    "/user",
    "/user/views",
)


class ConsentGateMiddleware:
    """Pure ASGI middleware enforcing the GDPR consent gate."""

    def __init__(self, app: ASGIApp, enabled: Optional[bool] = None):
        self.app = app
        if enabled is None:
            from computor_backend.settings import settings
            enabled = settings.CONSENT_GATE_ENABLED
        self.enabled = enabled

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http" or not self.enabled:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "GET")

        # required_version is set iff the request must be blocked. The check
        # runs in its own try so a Redis/DB failure fails open — and the
        # downstream app is invoked outside it, so endpoint exceptions
        # propagate normally instead of being swallowed here.
        required_version: Optional[str] = None
        if method != "OPTIONS" and not self._is_exempt(path, method):
            try:
                required_version = await self._blocked_version(scope)
            except Exception as e:
                logger.warning(f"Consent gate check failed, failing open: {e}")

        if required_version is not None:
            logger.info(f"Consent gate: blocked {method} {path}")
            response = JSONResponse(
                status_code=403,
                content={
                    "error": "consent_required",
                    "required_version": required_version,
                },
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)

    async def _blocked_version(self, scope: Scope) -> Optional[str]:
        """The policy version the caller still has to consent to, or None to allow."""
        principal = await resolve_principal_from_scope(scope)
        if principal is None:
            # Unauthenticated or unresolvable -> the route's auth dependency
            # is responsible (401); nothing for the consent gate to do.
            return None
        if principal.get("is_service"):
            return None

        from computor_backend.business_logic.consent import resolve_current_policy_version

        required_version = await resolve_current_policy_version()
        if required_version is None:
            # No policy configured -> gate inactive.
            return None

        user_id = str(principal["user_id"])
        if await self._has_consent(user_id, required_version):
            return None
        return required_version

    # ------------------------------------------------------------------
    # Whitelisting
    # ------------------------------------------------------------------

    def _is_exempt(self, path: str, method: str) -> bool:
        if path in EXEMPT_PATHS_EXACT:
            return True
        if method in ("GET", "HEAD") and path in EXEMPT_GET_PATHS_EXACT:
            return True
        return any(path.startswith(prefix) for prefix in EXEMPT_PATH_PREFIXES)

    # ------------------------------------------------------------------
    # Consent check (Redis first, DB fallback in threadpool)
    # ------------------------------------------------------------------

    async def _has_consent(self, user_id: str, required_version: str) -> bool:
        from computor_backend.business_logic.consent import (
            cache_consent_status,
            consent_cache_key,
        )
        from computor_backend.redis_cache import get_redis_client

        redis = await get_redis_client()
        cached = await redis.get(consent_cache_key(user_id, required_version))
        if cached is not None:
            return cached == "1"

        has_consent = await run_in_threadpool(self._db_has_consent, user_id, required_version)
        await cache_consent_status(user_id, required_version, has_consent)
        return has_consent

    @staticmethod
    def _db_has_consent(user_id: str, required_version: str) -> bool:
        from computor_backend.database import get_db_session
        from computor_backend.repositories.consent import ConsentRepository

        with get_db_session() as db:
            return ConsentRepository(db).get_active_consent(user_id, required_version) is not None
