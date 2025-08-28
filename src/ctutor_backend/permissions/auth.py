"""
Refactored authentication module that works with the new permission system.
This module provides a cleaner interface for authentication and principal creation.
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

from ctutor_backend.database import get_db
from ctutor_backend.gitlab_utils import gitlab_current_user
from ctutor_backend.interface.auth import GLPAuthConfig
from ctutor_backend.interface.tokens import decrypt_api_key
from ctutor_backend.model.auth import Account, User
from ctutor_backend.model.role import UserRole
from ctutor_backend.api.exceptions import NotFoundException, UnauthorizedException
from ctutor_backend.redis_cache import get_redis_client
import logging

# Import refactored permission components
from ctutor_backend.permissions.principal import Principal, build_claims
from ctutor_backend.permissions.core import db_get_claims, db_get_course_claims

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
            raise UnauthorizedException("Invalid credentials")
        
        user_id, user_password, user_type, token_expiration = results[0][:4]
        
        # Check token expiration for token users
        if user_type == 'token':
            now = datetime.datetime.now(datetime.timezone.utc)
            if token_expiration is None or token_expiration < now:
                raise UnauthorizedException("Token expired")
        
        # Verify password
        if password != decrypt_api_key(user_password):
            raise UnauthorizedException("Invalid credentials")
        
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
        """Authenticate using SSO token"""
        
        cache = await get_redis_client()
        session_key = f"sso_session:{token}"
        session_data = await cache.get(session_key)
        
        if not session_data:
            raise UnauthorizedException("Invalid or expired SSO token")
        
        try:
            session = json.loads(session_data)
            user_id = session.get("user_id")
            provider = session.get("provider", "sso")
            
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
            await cache.set(session_key, session_data, ttl=SSO_SESSION_TTL)
            
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
            await cache.set(cache_key, principal.model_dump_json(), ttl=AUTH_CACHE_TTL)
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
    if not authorization:
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
    This replaces get_current_permissions from the old system.
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


# Backward compatibility aliases
get_current_permissions = get_current_principal


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