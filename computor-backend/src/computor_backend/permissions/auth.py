"""
Authentication module for the Computor platform.

This module provides authentication services and principal creation for three authentication methods:

1. **Bearer Token Authentication (Recommended)**
   - Used after login via POST /auth/login
   - Tokens stored in Redis with configurable TTL
   - Supports both local and SSO authentication
   - Format: `Authorization: Bearer <token>`

2. **Basic Authentication (For automation/scripts only)**
   - Direct username/password authentication
   - Should NOT be used by frontend applications
   - Useful for API clients, CLI tools, CI/CD
   - Format: `Authorization: Basic <base64(username:password)>`

3. **SSO/OAuth Authentication**
   - Keycloak, GitLab, and other OAuth providers
   - Uses Bearer tokens after OAuth flow completes
   - Managed through /auth/{provider}/login endpoints

All authentication methods create a Principal object with user claims and permissions.
"""

import datetime
import json
import hashlib
import base64
import binascii
from typing import Annotated, Optional, List
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session
from fastapi.security import HTTPBasicCredentials
from gitlab import Gitlab
from fastapi import Depends, Request
from fastapi.security.utils import get_authorization_scheme_param

from computor_backend.database import get_db
from computor_backend.gitlab_utils import gitlab_current_user
from computor_types.auth import GLPAuthConfig
from computor_types.tokens import decrypt_api_key
from computor_backend.model.auth import Account, User
from computor_backend.model.role import UserRole
from computor_backend.api.exceptions import NotFoundException, UnauthorizedException
from computor_backend.redis_cache import get_redis_client
import logging

# Import refactored permission components
from computor_backend.permissions.principal import Principal, build_claims
from computor_backend.permissions.core import db_get_claims, db_get_course_claims

logger = logging.getLogger(__name__)

# Configuration
AUTH_CACHE_TTL = 10  # seconds
SSO_SESSION_TTL = 3600  # 1 hour for SSO sessions


class AuthenticationResult:
    """Result of authentication containing user info and roles"""
    
    def __init__(self, user_id: str, role_ids: List[str], provider: str = "unknown"):
        self.user_id = user_id
        self.role_ids = role_ids
        self.provider = provider


class AuthenticationService:
    """Service for handling different authentication methods"""
    
    @staticmethod
    def authenticate_basic(username: str, password: str, db: Session) -> AuthenticationResult:
        """Authenticate using basic auth credentials"""
        
        results = (
            db.query(
                User.id,
                User.password,
                User.user_type,
                User.token_expiration,
                UserRole.role_id
            )
            .outerjoin(UserRole, UserRole.user_id == User.id)
            .filter(or_(User.username == username, User.email == username))
            .all()
        )
        
        if not results:
            raise UnauthorizedException(error_code="AUTH_002", detail="Invalid credentials")
        
        user_id, user_password, user_type, token_expiration = results[0][:4]
        
        # Check token expiration for token users
        if user_type == 'token':
            now = datetime.datetime.now(datetime.timezone.utc)
            if token_expiration is None or token_expiration < now:
                raise UnauthorizedException(error_code="AUTH_003", detail="Token expired")
        
        # Verify password
        try:
            if user_password is None:
                raise UnauthorizedException(error_code="AUTH_002", detail="Invalid credentials")

            if password != decrypt_api_key(user_password):
                raise UnauthorizedException(error_code="AUTH_002", detail="Invalid credentials")
        except UnauthorizedException:
            # Re-raise our authentication exceptions
            raise
        except Exception as e:
            # Catch decryption errors (wrong secret, corrupted data, NULL password, etc.)
            # Log for debugging but return generic error to user
            import logging
            logging.error(f"Password verification failed for user '{username}': {str(e)}")
            raise UnauthorizedException(error_code="AUTH_002", detail="Invalid credentials")
        
        # Collect roles
        role_ids = [res[4] for res in results if res[4] is not None]
        
        return AuthenticationResult(user_id, role_ids, "basic")
    
    @staticmethod
    def authenticate_gitlab(gitlab_config: GLPAuthConfig, db: Session) -> AuthenticationResult:
        """Authenticate using GitLab credentials"""
        
        gl = Gitlab(url=gitlab_config.url, private_token=gitlab_config.token)
        
        try:
            user_dict = gitlab_current_user(gl)
        except Exception as e:
            logger.error(f"GitLab authentication failed: {e}")
            raise UnauthorizedException("GitLab authentication failed")
        
        results = (
            db.query(User.id, UserRole.role_id)
            .join(Account, Account.user_id == User.id)
            .outerjoin(UserRole, UserRole.user_id == User.id)
            .filter(
                Account.type == "gitlab",
                Account.provider_account_id == user_dict["username"]
            )
            .all()
        )
        
        if not results:
            raise NotFoundException("User not found")
        
        user_id = results[0][0]
        role_ids = [role_id for _, role_id in results if role_id is not None]
        
        return AuthenticationResult(user_id, role_ids, "gitlab")
    
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
            raise UnauthorizedException("SSO authentication failed")


class PrincipalBuilder:
    """Builder for creating Principal objects with proper claims"""
    
    @staticmethod
    def build(auth_result: AuthenticationResult, db: Session) -> Principal:
        """Build a Principal from authentication result"""
        
        # Get user claims from database
        claim_values = db_get_claims(auth_result.user_id, db)
        
        # Get course-specific claims
        course_claims = db_get_course_claims(auth_result.user_id, db)
        claim_values.extend(course_claims)
        
        # Build structured claims
        claims = build_claims(claim_values)
        
        # Create Principal
        return Principal(
            user_id=auth_result.user_id,
            roles=auth_result.role_ids,
            claims=claims
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


def parse_authorization_header(request: Request) -> Optional[GLPAuthConfig | HTTPBasicCredentials | SSOAuthCredentials]:
    """Parse authorization header to determine auth type"""

    # Check for GitLab credentials
    header_creds = request.headers.get("GLP-CREDS")
    if header_creds:
        try:
            gitlab_creds = json.loads(base64.b64decode(header_creds))
            return GLPAuthConfig(**gitlab_creds)
        except Exception as e:
            logger.error(f"Failed to parse GitLab credentials: {e}")
            raise UnauthorizedException("Invalid GitLab credentials")

    # Check for standard Authorization header
    authorization = request.headers.get("Authorization")

    # If no Authorization header, check for access_token cookie
    if not authorization:
        access_token = request.cookies.get("access_token")
        if access_token:
            logger.debug("Using access_token from cookie")
            return SSOAuthCredentials(token=access_token, scheme="Bearer")
        raise UnauthorizedException("No authorization provided")

    scheme, param = get_authorization_scheme_param(authorization)

    if not param:
        raise UnauthorizedException("Invalid authorization format")

    # Handle Bearer token (SSO)
    if scheme.lower() == "bearer":
        return SSOAuthCredentials(token=param, scheme="Bearer")

    # Handle Basic auth
    elif scheme.lower() == "basic":
        try:
            data = base64.b64decode(param).decode("ascii")
            username, separator, password = data.partition(":")
            if not separator:
                raise UnauthorizedException("Invalid Basic auth format")
            return HTTPBasicCredentials(username=username, password=password)
        except (ValueError, UnicodeDecodeError, binascii.Error) as e:
            logger.error(f"Failed to decode Basic auth: {e}")
            raise UnauthorizedException("Invalid Basic auth encoding")

    raise UnauthorizedException(f"Unsupported auth scheme: {scheme}")


async def get_current_principal(
    credentials: Annotated[
        GLPAuthConfig | HTTPBasicCredentials | SSOAuthCredentials,
        Depends(parse_authorization_header)
    ]
) -> Principal:
    """
    Main dependency for getting the current authenticated principal.
    This replaces get_current_principal from the old system.
    """

    with next(get_db()) as db:
        # Route to appropriate authentication method
        if isinstance(credentials, HTTPBasicCredentials):
            auth_result = AuthenticationService.authenticate_basic(
                credentials.username, credentials.password, db
            )

            # Build Principal without caching for basic auth
            return PrincipalBuilder.build(auth_result, db)

        elif isinstance(credentials, GLPAuthConfig):
            auth_result = AuthenticationService.authenticate_gitlab(credentials, db)

            # Build Principal with caching for GitLab auth
            cache_key = hashlib.sha256(
                f"{credentials.url}::{credentials.token}".encode()
            ).hexdigest()

            return await PrincipalBuilder.build_with_cache(auth_result, cache_key, db)

        elif isinstance(credentials, SSOAuthCredentials):
            auth_result = await AuthenticationService.authenticate_sso(
                credentials.token, db
            )

            # Build Principal with caching for SSO
            cache_key = hashlib.sha256(
                f"sso_permissions:{credentials.token}".encode()
            ).hexdigest()

            return await PrincipalBuilder.build_with_cache(auth_result, cache_key, db)

        else:
            raise UnauthorizedException("Unknown authentication type")


def parse_authorization_header_optional(request: Request) -> Optional[GLPAuthConfig | HTTPBasicCredentials | SSOAuthCredentials]:
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
        Optional[GLPAuthConfig | HTTPBasicCredentials | SSOAuthCredentials],
        Depends(parse_authorization_header_optional)
    ] = None
) -> Optional[Principal]:
    """
    Get current principal if valid credentials are provided, None otherwise.
    This allows endpoints to work with both authenticated and unauthenticated requests.
    Used for token refresh where the access token may be expired.
    """
    if not credentials:
        return None

    try:
        with next(get_db()) as db:
            # Route to appropriate authentication method
            if isinstance(credentials, HTTPBasicCredentials):
                auth_result = AuthenticationService.authenticate_basic(
                    credentials.username, credentials.password, db
                )
                return PrincipalBuilder.build(auth_result, db)

            elif isinstance(credentials, GLPAuthConfig):
                auth_result = AuthenticationService.authenticate_gitlab(credentials, db)
                cache_key = hashlib.sha256(
                    f"{credentials.url}::{credentials.token}".encode()
                ).hexdigest()
                return await PrincipalBuilder.build_with_cache(auth_result, cache_key, db)

            elif isinstance(credentials, SSOAuthCredentials):
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
        GLPAuthConfig | HTTPBasicCredentials | SSOAuthCredentials,
        Depends(parse_authorization_header)
    ]
) -> HeaderAuthCredentials:
    """Get information about the authentication method used"""
    
    if isinstance(credentials, GLPAuthConfig):
        return HeaderAuthCredentials(
            type="gitlab",
            credentials={"url": credentials.url}
        )
    
    elif isinstance(credentials, HTTPBasicCredentials):
        return HeaderAuthCredentials(
            type="basic",
            credentials={"username": credentials.username}
        )
    
    elif isinstance(credentials, SSOAuthCredentials):
        return HeaderAuthCredentials(
            type="sso",
            credentials={"scheme": credentials.scheme}
        )
    
    return HeaderAuthCredentials(type="unknown", credentials={})


def get_permissions_from_mockup(user_id: str) -> Principal:
    """
    Development/testing helper to create a Principal for a specific user.
    This should only be used in development environments.
    """
    
    try:
        with next(get_db()) as db:
            results = (
                db.query(User.id, UserRole.role_id)
                .select_from(User)
                .outerjoin(UserRole, UserRole.user_id == User.id)
                .filter(or_(User.id == user_id, User.username == user_id))
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
        raise UnauthorizedException("Mockup authentication failed")