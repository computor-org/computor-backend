"""Best-effort principal resolution for pure-ASGI middlewares.

Authentication in this codebase is a per-route dependency
(permissions/auth.py:get_current_principal), so no middleware ever sees a
resolved Principal. Middlewares that need the caller's identity (maintenance
admin bypass, consent gate) resolve it here from the caches the auth system
maintains, without running full authentication.

Credential precedence mirrors permissions/auth.py:parse_authorization_header
exactly (X-API-Token, then GLP-CREDS, then Authorization, then the
ct_access_token cookie only when no Authorization header is present), so the
identity a middleware acts on is the same one the route will authenticate.

Resolution sources per credential type:
- SSO tokens: principal cache; fallback to the sso_session store.
- API tokens: principal cache; fallback to a single indexed DB lookup
  (api_token.token_hash is a deterministic sha256).
- GLP-CREDS: principal cache only.
- HTTP Basic: NOT resolvable (would require password verification here);
  callers must treat these as unresolved.

Never raises: any Redis/DB failure resolves to None and is logged. Each
caller decides what None means (maintenance: not admin; consent gate: pass
through and let the route's auth dependency handle the request).
"""

import base64
import hashlib
import json
import logging
from typing import Optional

from starlette.concurrency import run_in_threadpool
from starlette.types import Scope

logger = logging.getLogger(__name__)


async def resolve_principal_from_scope(scope: Scope) -> Optional[dict]:
    """Resolve the request's principal as a plain dict.

    Returns at least {"user_id", "is_admin", "is_service"} on success, or
    None when the request carries no resolvable credentials.
    """
    try:
        headers = dict(scope.get("headers") or [])

        api_token = _decode(headers.get(b"x-api-token"))
        if api_token:
            principal = await _check_principal_cache("api_token_permissions", api_token)
            if principal is not None:
                return principal
            return await run_in_threadpool(_resolve_api_token_from_db, api_token)

        glp_creds = _decode(headers.get(b"glp-creds"))
        if glp_creds:
            return await _resolve_glp_creds(glp_creds)

        authorization = _decode(headers.get(b"authorization"))
        if authorization:
            scheme, _, param = authorization.partition(" ")
            if scheme.lower() == "bearer" and param.strip():
                return await _resolve_sso_token(param.strip())
            # Basic (or unknown scheme): not resolvable without verification.
            return None

        cookie_header = _decode(headers.get(b"cookie"))
        if cookie_header:
            token = _extract_cookie(cookie_header, "ct_access_token")
            if token:
                return await _resolve_sso_token(token)
    except Exception:
        logger.warning("Principal resolution from scope failed", exc_info=True)

    return None


async def _resolve_sso_token(token: str) -> Optional[dict]:
    principal = await _check_principal_cache("sso_permissions", token)
    if principal is not None:
        return principal

    # Principal cache expired but the session may still be live in Redis.
    from computor_backend.redis_cache import get_redis_client
    from computor_backend.utils.token_hash import hash_token

    redis = await get_redis_client()
    session_data = await redis.get(f"sso_session:{hash_token(token)}")
    if session_data:
        user_id = json.loads(session_data).get("user_id")
        if user_id:
            # Session store carries no role info; flags default conservatively.
            return {"user_id": str(user_id), "is_admin": False, "is_service": False}
    return None


async def _check_principal_cache(prefix: str, token: str) -> Optional[dict]:
    """Look up a cached Principal dict by credential prefix + token.

    The cache key is derived via permissions/auth.py:principal_cache_key so the
    shared principal cache stays byte-identical across this middleware and the
    auth dependency (a divergence here would silently miss every warm entry).
    """
    from computor_backend.redis_cache import get_redis_client
    from computor_backend.permissions.auth import principal_cache_key

    cache_key = principal_cache_key(prefix, token)
    redis = await get_redis_client()
    cached_data = await redis.get(cache_key)
    if not cached_data:
        return None
    principal_data = json.loads(cached_data)
    if not principal_data.get("user_id"):
        return None
    return principal_data


async def _resolve_glp_creds(header_value: str) -> Optional[dict]:
    """GLP-CREDS principal cache lookup (key: sha256(f"{url}::{token}"))."""
    from computor_backend.redis_cache import get_redis_client

    try:
        creds = json.loads(base64.b64decode(header_value))
        url, token = creds.get("url"), creds.get("token")
    except Exception:
        return None
    if not url or not token:
        return None
    cache_key = hashlib.sha256(f"{url}::{token}".encode()).hexdigest()
    redis = await get_redis_client()
    cached_data = await redis.get(cache_key)
    if not cached_data:
        return None
    principal_data = json.loads(cached_data)
    return principal_data if principal_data.get("user_id") else None


def _resolve_api_token_from_db(token: str) -> Optional[dict]:
    """One indexed lookup: api_token.token_hash (deterministic sha256) -> user."""
    from computor_backend.database import get_db_session
    from computor_backend.model.auth import User
    from computor_backend.model.service import ApiToken
    from computor_backend.utils.api_token import hash_api_token, validate_token_format

    if not validate_token_format(token):
        return None
    token_hash = hash_api_token(token)
    with get_db_session() as db:
        row = (
            db.query(ApiToken.user_id, User.is_service)
            .join(User, User.id == ApiToken.user_id)
            .filter(ApiToken.token_hash == token_hash, ApiToken.revoked_at.is_(None))
            .first()
        )
        if row is None:
            return None
        return {"user_id": str(row.user_id), "is_admin": False, "is_service": bool(row.is_service)}


def _decode(value) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    return value or ""


def _extract_cookie(cookie_header: str, name: str) -> Optional[str]:
    for part in cookie_header.split(";"):
        part = part.strip()
        if part.startswith(f"{name}="):
            return part[len(name) + 1:]
    return None
