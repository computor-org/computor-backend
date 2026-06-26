"""
Authentication module for the Computor platform.

Supported authentication methods:

1. **Bearer Token (SSO)** — tokens from Keycloak/OAuth flow (`Authorization: Bearer <token>`)
2. **API Token** — `X-API-Token` header (services and automation)

All methods create a Principal with user claims and permissions.
"""

import datetime
import json
import hashlib
import binascii
from typing import Annotated, Optional, List
from pydantic import BaseModel
from sqlalchemy.orm import Session
from fastapi import Depends, Request
from fastapi.security.utils import get_authorization_scheme_param

from computor_backend.database import get_db_session
from computor_backend.model.auth import User
from computor_backend.model.role import UserRole
from computor_backend.model.service import ApiToken
from computor_backend.exceptions import NotFoundException, UnauthorizedException
from computor_backend.redis_cache import get_redis_client
from computor_backend.utils.api_token import hash_api_token, validate_token_format
import logging

# Import refactored permission components
from computor_backend.permissions.principal import Principal, build_claims
from computor_backend.permissions.core import (
    db_get_claims,
    db_get_course_claims,
    db_get_organization_claims,
    db_get_course_family_claims,
)

logger = logging.getLogger(__name__)

# Configuration
AUTH_CACHE_TTL = 900  # 15 minutes - balanced performance vs permission freshness
SSO_SESSION_TTL = 3600  # 1 hour for SSO sessions
# Note: Can increase AUTH_CACHE_TTL to 3600s (1 hour) when implementing cache invalidation
# on role/permission PATCH endpoints for even better performance


class AuthenticationResult:
    """Result of authentication containing user info and roles"""
    
    def __init__(self, user_id: str, role_ids: List[str], provider: str = "unknown"):
        self.user_id = user_id
        self.role_ids = role_ids
        self.provider = provider


class AuthenticationService:
    """Service for handling different authentication methods"""

    @staticmethod
    async def authenticate_sso(token: str, db: Session) -> AuthenticationResult:
        """Authenticate using SSO token with hashed token lookup"""

        from computor_backend.redis_cache import get_redis_client
        from computor_backend.utils.token_hash import hash_token

        redis_client = await get_redis_client()

        # Hash token for lookup
        token_hash = hash_token(token)
        session_key = f"sso_session:{token_hash}"
        session_data_raw = await redis_client.get(session_key)

        if not session_data_raw:
            raise UnauthorizedException("Invalid or expired SSO token")

        try:
            session_data = json.loads(session_data_raw)
            user_id = session_data.get("user_id")
            provider = session_data.get("provider", "sso")

            if not user_id:
                raise UnauthorizedException("Invalid session data")

            # Get user roles
            results = (
                db.query(UserRole.role_id)
                .filter(UserRole.user_id == user_id)
                .all()
            )

            role_ids = [r[0] for r in results if r[0] is not None]

            # Refresh session TTL
            await redis_client.set(session_key, session_data_raw, ex=SSO_SESSION_TTL)

            logger.info(f"SSO authentication successful for user {user_id} via {provider}")
            return AuthenticationResult(user_id, role_ids, provider)

        except json.JSONDecodeError:
            raise UnauthorizedException("Invalid session data format")
        except Exception as e:
            logger.error(f"Error during SSO authentication: {e}")
            raise UnauthorizedException("SSO authentication failed") from e

    @staticmethod
    async def authenticate_api_token(token: str, db: Session) -> AuthenticationResult:
        """
        Authenticate using API token (with Redis caching).

        API tokens provide scoped authentication for services and automation.
        Token format: ctp_<random_32_chars>

        Caching strategy:
        - Token validation results cached in Redis for fast auth
        - Cache invalidated on token revocation

        Args:
            token: The full API token string
            db: Database session

        Returns:
            AuthenticationResult with user_id, roles, and scopes

        Raises:
            UnauthorizedException: If token is invalid, revoked, or expired
        """
        from computor_backend.permissions.api_token_cache import (
            get_cached_token_data,
            set_cached_token_data,
            track_user_token,
            CachedTokenData,
        )

        # Validate token format
        if not validate_token_format(token):
            raise UnauthorizedException(error_code="AUTH_004", detail="Invalid API token format")

        # Hash token for lookup
        token_hash = hash_api_token(token)
        token_hash_hex = token_hash.hex()

        # Try cache first
        cached = await get_cached_token_data(token_hash_hex)

        if cached:
            # Cache hit - return cached auth result
            auth_result = AuthenticationResult(cached.user_id, cached.role_ids, "api_token")
            auth_result.scopes = cached.scopes
            return auth_result

        # Cache miss - query database
        api_token = (
            db.query(ApiToken)
            .filter(
                ApiToken.token_hash == token_hash,
                ApiToken.revoked_at.is_(None)
            )
            .first()
        )

        if not api_token:
            logger.warning(f"API token authentication failed: token not found or revoked")
            raise UnauthorizedException(error_code="AUTH_004", detail="Invalid or revoked API token")

        # Check expiration
        if api_token.expires_at:
            now = datetime.datetime.now(datetime.timezone.utc)
            if api_token.expires_at < now:
                logger.warning(f"API token {api_token.id} has expired")
                raise UnauthorizedException(error_code="AUTH_005", detail="API token expired")

        # Update usage stats (direct DB write on cache miss only)
        api_token.last_used_at = datetime.datetime.now(datetime.timezone.utc)
        api_token.usage_count += 1
        db.commit()

        # Get user roles
        role_ids = (
            db.query(UserRole.role_id)
            .filter(UserRole.user_id == api_token.user_id)
            .all()
        )
        role_ids = [r[0] for r in role_ids if r[0] is not None]

        # Cache the token data
        token_data = CachedTokenData(
            token_id=str(api_token.id),
            user_id=str(api_token.user_id),
            role_ids=role_ids,
            scopes=api_token.scopes or [],
            expires_at=api_token.expires_at.isoformat() if api_token.expires_at else None,
            token_prefix=api_token.token_prefix,
        )
        await set_cached_token_data(token_hash_hex, token_data)
        await track_user_token(str(api_token.user_id), token_hash_hex)

        logger.info(f"API token authentication successful for user {api_token.user_id} (token: {api_token.token_prefix}...)")

        # Create authentication result with scopes
        auth_result = AuthenticationResult(api_token.user_id, role_ids, "api_token")
        auth_result.scopes = api_token.scopes

        return auth_result


class PrincipalBuilder:
    """Builder for creating Principal objects with proper claims"""
    
    @staticmethod
    def build(auth_result: AuthenticationResult, db: Session) -> Principal:
        """Build a Principal from authentication result"""

        # Get user claims from database
        claim_values = db_get_claims(auth_result.user_id, db)

        # Get scoped claims (course / organization / course_family). Each
        # emits ``("permissions", "<scope>:<role>:<scope_id>")`` tuples
        # which build_claims files under Claims.dependent[<scope>].
        claim_values.extend(db_get_course_claims(auth_result.user_id, db))
        claim_values.extend(db_get_organization_claims(auth_result.user_id, db))
        claim_values.extend(db_get_course_family_claims(auth_result.user_id, db))

        # Convert API token scopes to claims (if present)
        # API token scopes use the same format as claims: "resource:action" or "resource:action:resource_id"
        if hasattr(auth_result, 'scopes') and auth_result.scopes:
            for scope in auth_result.scopes:
                # Convert scope to claim format: ("permissions", scope)
                claim_values.append(("permissions", scope))
            logger.debug(f"Added {len(auth_result.scopes)} API token scopes as claims for user {auth_result.user_id}")

        # Build structured claims
        claims = build_claims(claim_values)

        # Surface ``User.is_service`` on the principal so endpoints can
        # distinguish a worker / system account from a regular user
        # without re-querying the DB. Used by worker-facing endpoints
        # (e.g. tutor test ``input/download``) to bypass per-user
        # ownership checks for the test-runner service account.
        is_service = bool(
            db.query(User.is_service)
            .filter(User.id == auth_result.user_id)
            .scalar()
        )

        # Create Principal
        return Principal(
            user_id=auth_result.user_id,
            roles=auth_result.role_ids,
            claims=claims,
            is_service=is_service,
        )
    
    @staticmethod
    async def build_with_cache(auth_result: AuthenticationResult, 
                              cache_key: str, db: Session) -> Principal:
        """Build Principal with caching support"""
        
        cache = await get_redis_client()
        
        # Try to get from cache
        try:
            cached_data = await cache.get(cache_key)
            if cached_data:
                logger.debug(f"Principal cache hit for {cache_key}")
                return Principal.model_validate(json.loads(cached_data), from_attributes=True)
        except Exception as e:
            logger.warning(f"Cache retrieval error: {e}")
        
        # Build new Principal
        principal = PrincipalBuilder.build(auth_result, db)
        
        # Cache it
        try:
            await cache.set(cache_key, principal.model_dump_json(), ex=AUTH_CACHE_TTL)
            logger.debug(f"Cached Principal for {cache_key}")
        except Exception as e:
            logger.warning(f"Cache storage error: {e}")
        
        return principal


class SSOAuthCredentials(BaseModel):
    """SSO Bearer token credentials"""
    token: str
    scheme: str = "Bearer"


class ApiTokenCredentials(BaseModel):
    """API Token credentials (X-API-Token header)"""
    token: str
    scheme: str = "ApiToken"


def parse_authorization_header(request: Request) -> Optional[SSOAuthCredentials | ApiTokenCredentials]:
    """Parse authorization header to determine auth type"""

    # Check for API Token header (X-API-Token) - highest priority for services
    api_token = request.headers.get("X-API-Token")
    if api_token:
        logger.debug("Using API token from X-API-Token header")
        return ApiTokenCredentials(token=api_token)

    # Check for standard Authorization header
    authorization = request.headers.get("Authorization")

    # If no Authorization header, check for access_token cookie
    if not authorization:
        access_token = request.cookies.get("ct_access_token")
        if access_token:
            logger.debug("Using access_token from cookie")
            return SSOAuthCredentials(token=access_token, scheme="Bearer")
        raise UnauthorizedException("No authorization provided")

    scheme, param = get_authorization_scheme_param(authorization)

    if not param:
        raise UnauthorizedException("Invalid authorization format")

    if scheme.lower() == "bearer":
        return SSOAuthCredentials(token=param, scheme="Bearer")

    raise UnauthorizedException(f"Unsupported auth scheme: {scheme}")


async def get_current_principal(
    credentials: Annotated[
        SSOAuthCredentials | ApiTokenCredentials,
        Depends(parse_authorization_header)
    ]
) -> Principal:
    """
    Main dependency for getting the current authenticated principal.

    Supports: API Token (X-API-Token), SSO Bearer token.
    """

    # For cacheable auth methods, check cache FIRST before creating DB connection
    cache_key = None
    if isinstance(credentials, ApiTokenCredentials):
        cache_key = hashlib.sha256(
            f"api_token_permissions:{credentials.token}".encode()
        ).hexdigest()
    elif isinstance(credentials, SSOAuthCredentials):
        cache_key = hashlib.sha256(
            f"sso_permissions:{credentials.token}".encode()
        ).hexdigest()

    # Try cache first (no DB connection!)
    if cache_key:
        cache = await get_redis_client()
        try:
            cached_data = await cache.get(cache_key)
            if cached_data:
                logger.debug(f"Principal cache HIT for {cache_key[:16]}... (no DB connection)")
                return Principal.model_validate(json.loads(cached_data), from_attributes=True)
        except Exception as e:
            logger.warning(f"Cache retrieval error: {e}")

    # Cache miss or non-cacheable auth - create DB connection
    logger.debug(f"Principal cache MISS, creating DB connection")
    with get_db_session() as db:
        # Route to appropriate authentication method
        if isinstance(credentials, ApiTokenCredentials):
            auth_result = await AuthenticationService.authenticate_api_token(
                credentials.token, db
            )
            principal = PrincipalBuilder.build(auth_result, db)

        elif isinstance(credentials, SSOAuthCredentials):
            auth_result = await AuthenticationService.authenticate_sso(
                credentials.token, db
            )
            principal = PrincipalBuilder.build(auth_result, db)

        else:
            raise UnauthorizedException("Unknown authentication type")

        # Cache the result (if cacheable)
        if cache_key:
            try:
                cache = await get_redis_client()
                await cache.set(cache_key, principal.model_dump_json(), ex=AUTH_CACHE_TTL)
                logger.debug(f"Cached Principal for {cache_key[:16]}...")
            except Exception as e:
                logger.warning(f"Cache storage error: {e}")

        return principal


def parse_authorization_header_optional(request: Request) -> Optional[SSOAuthCredentials | ApiTokenCredentials]:
    """
    Parse authorization header but return None instead of raising exception.
    Used for endpoints that accept but don't require authentication (like token refresh).
    """
    try:
        return parse_authorization_header(request)
    except UnauthorizedException:
        return None


async def get_current_principal_optional(
    request: Request,
    credentials: Annotated[
        Optional[SSOAuthCredentials | ApiTokenCredentials],
        Depends(parse_authorization_header_optional)
    ] = None
) -> Optional[Principal]:
    """
    Get current principal if valid credentials are provided, None otherwise.
    Used for endpoints that accept but don't require authentication.
    """
    if not credentials:
        return None

    try:
        with get_db_session() as db:
            if isinstance(credentials, SSOAuthCredentials):
                auth_result = await AuthenticationService.authenticate_sso(
                    credentials.token, db
                )
                cache_key = hashlib.sha256(
                    f"sso_permissions:{credentials.token}".encode()
                ).hexdigest()
                return await PrincipalBuilder.build_with_cache(auth_result, cache_key, db)

            else:
                return None
    except (UnauthorizedException, Exception) as e:
        # If authentication fails (e.g., expired token), return None
        logger.debug(f"Optional authentication failed: {e}")
        return None


class HeaderAuthCredentials(BaseModel):
    """Information about the authentication method used"""
    type: str
    credentials: dict


def get_auth_credentials(
    credentials: Annotated[
        SSOAuthCredentials | ApiTokenCredentials,
        Depends(parse_authorization_header)
    ]
) -> HeaderAuthCredentials:
    """Get information about the authentication method used"""

    if isinstance(credentials, SSOAuthCredentials):
        return HeaderAuthCredentials(
            type="sso",
            credentials={"scheme": credentials.scheme}
        )

    elif isinstance(credentials, ApiTokenCredentials):
        return HeaderAuthCredentials(
            type="api_token",
            credentials={}
        )

    return HeaderAuthCredentials(type="unknown", credentials={})


def get_permissions_from_mockup(user_id: str) -> Principal:
    """
    Development/testing helper to create a Principal for a specific user.
    This should only be used in development environments.
    """
    
    try:
        with get_db_session() as db:
            results = (
                db.query(User.id, UserRole.role_id)
                .select_from(User)
                .outerjoin(UserRole, UserRole.user_id == User.id)
                .filter(User.id == user_id)
                .all()
            )
            
            if not results:
                raise NotFoundException(f"User {user_id} not found")
            
            actual_user_id = results[0][0]
            role_ids = [r[1] for r in results if r[1] is not None]
            
            # Build authentication result
            auth_result = AuthenticationResult(actual_user_id, role_ids, "mockup")
            
            # Build Principal
            return PrincipalBuilder.build(auth_result, db)
            
    except Exception as e:
        logger.error(f"Mockup auth error: {e}")
        raise UnauthorizedException("Mockup authentication failed") from e