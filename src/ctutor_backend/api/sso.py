"""
Generic SSO authentication API endpoints.
"""

import secrets
from typing import Dict, List, Optional
from urllib.parse import urlencode
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ctutor_backend.database import get_db
from ctutor_backend.permissions.auth import get_current_principal
from ctutor_backend.api.exceptions import UnauthorizedException, BadRequestException, NotFoundException
from ctutor_backend.permissions.principal import Principal
from ctutor_backend.model.auth import User, Account
from ctutor_backend.model.role import UserRole
from ctutor_backend.plugins import PluginMetadata, AuthStatus, UserInfo
from ctutor_backend.plugins.registry import get_plugin_registry
from ctutor_backend.redis_cache import get_redis_client
from ctutor_backend.auth.keycloak_admin import KeycloakAdminClient, KeycloakUser
import json
import logging

logger = logging.getLogger(__name__)

sso_router = APIRouter(prefix="/auth")


class ProviderInfo(BaseModel):
    """Information about an authentication provider."""
    name: str = Field(..., description="Provider name")
    display_name: str = Field(..., description="Display name")
    type: str = Field(..., description="Authentication type")
    enabled: bool = Field(..., description="Whether provider is enabled")
    login_url: Optional[str] = Field(None, description="Login URL if applicable")


class LoginRequest(BaseModel):
    """Login request for SSO."""
    provider: str = Field(..., description="Provider name")
    redirect_uri: Optional[str] = Field(None, description="Redirect URI after login")


class CallbackRequest(BaseModel):
    """OAuth callback parameters."""
    code: str = Field(..., description="Authorization code")
    state: Optional[str] = Field(None, description="State parameter")


class SSOAuthResponse(BaseModel):
    """Response after successful SSO authentication."""
    user_id: str = Field(..., description="User ID")
    account_id: str = Field(..., description="Account ID")
    access_token: Optional[str] = Field(None, description="Access token if available")
    is_new_user: bool = Field(..., description="Whether this is a new user")


class UserRegistrationRequest(BaseModel):
    """User registration request."""
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: str = Field(..., description="Email address")
    password: str = Field(..., min_length=8, description="Password")
    given_name: str = Field(..., min_length=1, description="First name")
    family_name: str = Field(..., min_length=1, description="Last name")
    provider: str = Field("keycloak", description="Authentication provider to register with")
    send_verification_email: bool = Field(True, description="Send email verification")


class UserRegistrationResponse(BaseModel):
    """Response after successful user registration."""
    user_id: str = Field(..., description="User ID in Computor")
    provider_user_id: str = Field(..., description="User ID in authentication provider")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    message: str = Field(..., description="Success message")


class TokenRefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str = Field(..., description="Refresh token from initial authentication")
    provider: str = Field("keycloak", description="Authentication provider")


class TokenRefreshResponse(BaseModel):
    """Response after successful token refresh."""
    access_token: str = Field(..., description="New access token")
    expires_in: Optional[int] = Field(None, description="Token expiration time in seconds")
    refresh_token: Optional[str] = Field(None, description="New refresh token if rotated")


@sso_router.get("/providers", response_model=List[ProviderInfo])
async def list_providers():
    """
    List available authentication providers.
    
    Returns all enabled authentication providers with their metadata.
    """
    registry = get_plugin_registry()
    providers = []
    
    # Debug logging
    logger.info(f"Registry enabled plugins: {registry.get_enabled_plugins()}")
    logger.info(f"Registry loaded plugins: {registry.get_loaded_plugins()}")
    
    for plugin_name in registry.get_enabled_plugins():
        metadata = registry.get_plugin_metadata(plugin_name)
        logger.info(f"Plugin {plugin_name} metadata: {metadata}")
        if metadata:
            providers.append(ProviderInfo(
                name=plugin_name,
                display_name=metadata.provider_name,
                type=metadata.provider_type.value,
                enabled=True,
                login_url=f"/auth/{plugin_name}/login"
            ))
    
    return providers


@sso_router.get("/{provider}/login")
async def initiate_login(
    provider: str,
    redirect_uri: Optional[str] = Query(None, description="Redirect URI after authentication"),
    request: Request = None
):
    """
    Initiate SSO login for a specific provider.
    
    Redirects the user to the provider's login page.
    """
    registry = get_plugin_registry()
    
    # Debug logging
    logger.info(f"Attempting login for provider: {provider}")
    logger.info(f"Provider type: {type(provider)}")
    logger.info(f"Provider repr: {repr(provider)}")
    enabled_plugins = registry.get_enabled_plugins()
    logger.info(f"Enabled plugins: {enabled_plugins}")
    logger.info(f"Enabled plugins type: {type(enabled_plugins)}")
    logger.info(f"Loaded plugins: {registry.get_loaded_plugins()}")
    logger.info(f"Provider in enabled_plugins: {provider in enabled_plugins}")
    
    # Check if provider exists and is enabled
    if provider not in registry.get_enabled_plugins():
        raise NotFoundException(f"Authentication provider not found or not enabled: {provider}")
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    
    # Store state in Redis with 10 minute expiration
    redis_client = await get_redis_client()
    state_data = {
        "provider": provider,
        "redirect_uri": redirect_uri or str(request.url_for("sso_success")),
        "timestamp": str(request.headers.get("date", ""))
    }
    await redis_client.set(
        f"sso_state:{state}",
        json.dumps(state_data),
        ttl=600  # 10 minutes
    )
    
    # Get callback URL
    callback_url = str(request.url_for("handle_callback", provider=provider))
    
    try:
        # Get login URL from provider
        login_url = registry.get_login_url(provider, callback_url, state)
        
        # Redirect to provider login
        return RedirectResponse(url=login_url, status_code=302)
        
    except Exception as e:
        logger.error(f"Failed to initiate login for {provider}: {e}")
        logger.error(f"Exception type: {type(e)}")
        logger.error(f"Exception traceback:", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to initiate login: {str(e)}")


@sso_router.get("/{provider}/callback", name="handle_callback")
async def handle_callback(
    provider: str,
    code: str = Query(..., description="Authorization code"),
    state: Optional[str] = Query(None, description="State parameter"),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback from provider.
    
    Exchanges the authorization code for tokens and creates/updates user account.
    """
    registry = get_plugin_registry()
    redis_client = await get_redis_client()
    
    # Validate state parameter
    if state:
        state_key = f"sso_state:{state}"
        state_data_raw = await redis_client.get(state_key)
        
        if not state_data_raw:
            raise BadRequestException("Invalid or expired state parameter")
        
        state_data = json.loads(state_data_raw)
        
        # Delete state to prevent replay attacks
        await redis_client.delete(state_key)
        
        # Validate provider matches
        if state_data["provider"] != provider:
            raise BadRequestException("Provider mismatch in state parameter")
    
    try:
        # Get the callback URL (same as used in the original authorization request)
        callback_url = str(request.url_for("handle_callback", provider=provider))
        
        # Handle callback with provider
        auth_result = await registry.handle_callback(provider, code, state, callback_url)
        
        if auth_result.status != AuthStatus.SUCCESS:
            raise UnauthorizedException(f"Authentication failed: {auth_result.error_message}")
        
        # Get user info
        user_info = auth_result.user_info
        if not user_info:
            raise BadRequestException("No user information received from provider")
        
        # Find or create user account
        account = db.query(Account).filter(
            Account.provider == provider,
            Account.type == registry.get_plugin_metadata(provider).provider_type.value,
            Account.provider_account_id == user_info.provider_id
        ).first()
        
        is_new_user = False
        
        if account:
            # Existing account - get user
            user = account.user
            
            # Update account properties with latest info
            account.properties = {
                "email": user_info.email,
                "username": user_info.username,
                "picture": user_info.picture,
                "groups": user_info.groups,
                "attributes": user_info.attributes,
                "last_login": str(auth_result.expires_at) if auth_result.expires_at else None
            }
            
        else:
            # New account - create user
            is_new_user = True
            
            # Create new user
            user = User(
                given_name=user_info.given_name or "",
                family_name=user_info.family_name or "",
                username=user_info.username or user_info.email or f"{provider}_{user_info.provider_id}",
                email=user_info.email
            )
            db.add(user)
            db.flush()
            
            # Create account
            account = Account(
                provider=provider,
                type=registry.get_plugin_metadata(provider).provider_type.value,
                provider_account_id=user_info.provider_id,
                user_id=user.id,
                properties={
                    "email": user_info.email,
                    "username": user_info.username,
                    "picture": user_info.picture,
                    "groups": user_info.groups,
                    "attributes": user_info.attributes,
                    "last_login": str(auth_result.expires_at) if auth_result.expires_at else None
                }
            )
            db.add(account)
            
            # Note: No default role assigned to SSO users
            # Roles should be assigned based on groups/claims from the provider
            # or manually by an administrator
        
        db.commit()
        
        # Generate API session token for the user
        api_session_token = secrets.token_urlsafe(32)
        session_data = {
            "user_id": str(user.id),
            "account_id": str(account.id),
            "provider": provider,
            "username": user.username,
            "email": user.email,
            "created_at": str(datetime.now(timezone.utc))
        }
        
        # Store session in Redis with TTL
        session_key = f"sso_session:{api_session_token}"
        await redis_client.set(
            session_key,
            json.dumps(session_data),
            ttl=86400  # 24 hours
        )
        
        # Store tokens in Redis if available
        if auth_result.access_token:
            token_key = f"sso_token:{provider}:{user.id}"
            token_data = {
                "access_token": auth_result.access_token,
                "refresh_token": auth_result.refresh_token,
                "expires_at": str(auth_result.expires_at) if auth_result.expires_at else None
            }
            
            # Store with appropriate expiration
            expiration = 3600  # Default 1 hour
            if auth_result.expires_at:
                # Calculate seconds until expiration
                now = datetime.now(timezone.utc)
                delta = auth_result.expires_at - now
                expiration = max(int(delta.total_seconds()), 60)  # At least 1 minute
            
            await redis_client.set(
                token_key,
                json.dumps(token_data),
                ttl=expiration
            )
        
        # Get redirect URI from state or use default
        redirect_uri = "/"
        if state and "redirect_uri" in state_data:
            redirect_uri = state_data["redirect_uri"]
        
        # Create response with user info
        response_data = SSOAuthResponse(
            user_id=str(user.id),
            account_id=str(account.id),
            access_token=api_session_token,  # Use our API session token instead of provider token
            is_new_user=is_new_user
        )
        
        # Redirect with encoded response
        params = {
            "user_id": response_data.user_id,
            "account_id": response_data.account_id,
            "is_new_user": str(response_data.is_new_user).lower(),
            "token": api_session_token,  # Include token in redirect
            "refresh_token": auth_result.refresh_token if auth_result.refresh_token else ""  # Include refresh token
        }
        
        if "?" in redirect_uri:
            redirect_url = f"{redirect_uri}&{urlencode(params)}"
        else:
            redirect_url = f"{redirect_uri}?{urlencode(params)}"
        
        return RedirectResponse(url=redirect_url, status_code=302)
        
    except Exception as e:
        logger.error(f"Failed to handle callback for {provider}: {e}")
        
        # Redirect to error page
        error_params = {"error": str(e), "provider": provider}
        error_url = f"/?{urlencode(error_params)}"
        return RedirectResponse(url=error_url, status_code=302)


@sso_router.get("/success", name="sso_success")
async def sso_success():
    """Default success page after SSO authentication."""
    return {"message": "Authentication successful", "status": "success"}


@sso_router.get("/me", dependencies=[Depends(get_current_principal)])
async def get_current_user_info(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user information.
    
    This endpoint can be used to test SSO authentication and retrieve
    the current user's details and roles.
    """
    # Get user from database
    user = db.query(User).filter(User.id == principal.user_id).first()
    
    if not user:
        raise NotFoundException("User not found")
    
    # Get user's accounts
    accounts = db.query(Account).filter(Account.user_id == user.id).all()
    
    # Get user roles
    user_roles = db.query(UserRole).filter(UserRole.user_id == user.id).all()
    role_names = [ur.role.id for ur in user_roles if ur.role]
    
    return {
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "given_name": user.given_name,
            "family_name": user.family_name,
            "user_type": user.user_type
        },
        "roles": role_names + principal.roles,  # Include both DB roles and principal roles
        "principal_roles": principal.roles,  # Original principal roles
        "db_roles": role_names,  # Roles from database
        "accounts": [
            {
                "provider": acc.provider,
                "type": acc.type,
                "provider_account_id": acc.provider_account_id
            }
            for acc in accounts
        ],
        "authenticated_via": "sso" if any(acc.provider in ["keycloak", "gitlab"] for acc in accounts) else "basic"
    }


@sso_router.post("/{provider}/logout")
async def logout(
    provider: str,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db)
):
    """
    Logout from a specific provider.
    
    Revokes tokens and performs provider-specific logout if supported.
    """
    registry = get_plugin_registry()
    redis_client = await get_redis_client()
    
    # Check if provider exists and is enabled
    if provider not in registry.get_enabled_plugins():
        raise NotFoundException(f"Authentication provider not found or not enabled: {provider}")
    
    # Get stored tokens
    token_key = f"sso_token:{provider}:{principal.user_id}"
    token_data_raw = await redis_client.get(token_key)
    
    if token_data_raw:
        token_data = json.loads(token_data_raw)
        access_token = token_data.get("access_token")
        
        if access_token:
            try:
                # Perform provider logout
                plugin = registry.get_plugin(provider)
                if plugin:
                    await plugin.logout(access_token)
            except Exception as e:
                logger.error(f"Failed to logout from {provider}: {e}")
        
        # Delete stored tokens
        await redis_client.delete(token_key)
    
    return {"message": "Logout successful", "provider": provider}


@sso_router.get("/admin/plugins", dependencies=[Depends(get_current_principal)])
async def list_all_plugins(principal: Principal = Depends(get_current_principal)):
    """
    List all available plugins (admin only).
    
    Shows both enabled and disabled plugins with full metadata.
    """
    # Check admin permission
    if "_admin" not in principal.roles:
        raise UnauthorizedException("Admin access required")
    
    registry = get_plugin_registry()
    
    plugins = {}
    
    # Get all discovered plugins
    discovered = registry.loader.discover_plugins()
    
    for plugin_name in discovered:
        metadata = registry.get_plugin_metadata(plugin_name)
        if metadata:
            plugins[plugin_name] = {
                "metadata": metadata.model_dump(),
                "enabled": plugin_name in registry.get_enabled_plugins(),
                "loaded": plugin_name in registry.get_loaded_plugins()
            }
    
    return plugins


@sso_router.post("/admin/plugins/{plugin_name}/enable", dependencies=[Depends(get_current_principal)])
async def enable_plugin(
    plugin_name: str,
    principal: Principal = Depends(get_current_principal)
):
    """Enable a plugin (admin only)."""
    # Check admin permission
    if "_admin" not in principal.roles:
        raise UnauthorizedException("Admin access required")
    
    registry = get_plugin_registry()
    
    # Enable plugin
    registry.enable_plugin(plugin_name)
    
    # Try to load it
    try:
        await registry.load_plugin(plugin_name)
        return {"message": f"Plugin {plugin_name} enabled and loaded"}
    except Exception as e:
        return {"message": f"Plugin {plugin_name} enabled but failed to load: {e}"}


@sso_router.post("/admin/plugins/{plugin_name}/disable", dependencies=[Depends(get_current_principal)])
async def disable_plugin(
    plugin_name: str,
    principal: Principal = Depends(get_current_principal)
):
    """Disable a plugin (admin only)."""
    # Check admin permission
    if "_admin" not in principal.roles:
        raise UnauthorizedException("Admin access required")
    
    registry = get_plugin_registry()
    
    # Unload if loaded
    await registry.unload_plugin(plugin_name)
    
    # Disable plugin
    registry.disable_plugin(plugin_name)
    
    return {"message": f"Plugin {plugin_name} disabled"}


@sso_router.post("/admin/plugins/reload", dependencies=[Depends(get_current_principal)])
async def reload_plugins(principal: Principal = Depends(get_current_principal)):
    """Reload all plugins (admin only)."""
    # Check admin permission
    if "_admin" not in principal.roles:
        raise UnauthorizedException("Admin access required")
    
    registry = get_plugin_registry()
    await registry.reload_all()
    
    return {
        "message": "Plugins reloaded",
        "loaded": registry.get_loaded_plugins()
    }


@sso_router.post("/register", response_model=UserRegistrationResponse)
async def register_user(
    request: UserRegistrationRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user with SSO provider.
    
    Creates user in both the authentication provider and local database.
    """
    # Validate provider
    registry = get_plugin_registry()
    if request.provider not in registry.get_enabled_plugins():
        raise BadRequestException(f"Authentication provider not enabled: {request.provider}")
    
    # Check if user already exists in local database
    existing_user = db.query(User).filter(
        (User.username == request.username) | (User.email == request.email)
    ).first()
    
    if existing_user:
        raise BadRequestException("User with this username or email already exists")
    
    try:
        # Create user in authentication provider
        if request.provider == "keycloak":
            keycloak_admin = KeycloakAdminClient()
            
            # Check if user exists in Keycloak
            if await keycloak_admin.user_exists(request.username):
                raise BadRequestException("User already exists in Keycloak")
            
            # Create Keycloak user
            keycloak_user = KeycloakUser(
                username=request.username,
                email=request.email,
                firstName=request.given_name,
                lastName=request.family_name,
                enabled=True,
                emailVerified=False,
                credentials=[{
                    "type": "password",
                    "value": request.password,
                    "temporary": False
                }]
            )
            
            provider_user_id = await keycloak_admin.create_user(keycloak_user)
            
            # Send verification email if requested
            if request.send_verification_email and request.email:
                try:
                    await keycloak_admin.send_verify_email(provider_user_id)
                except Exception as e:
                    logger.warning(f"Failed to send verification email: {e}")
        else:
            raise BadRequestException(f"Registration not implemented for provider: {request.provider}")
        
        # Create user in local database
        local_user = User(
            given_name=request.given_name,
            family_name=request.family_name,
            username=request.username,
            email=request.email
        )
        db.add(local_user)
        db.flush()
        
        # Create account linking to provider
        account = Account(
            provider=request.provider,
            type="oidc",  # Keycloak uses OIDC
            provider_account_id=provider_user_id,
            user_id=local_user.id,
            properties={
                "email": request.email,
                "username": request.username,
                "registration_date": str(datetime.now(timezone.utc))
            }
        )
        db.add(account)
        
        db.commit()
        
        return UserRegistrationResponse(
            user_id=str(local_user.id),
            provider_user_id=provider_user_id,
            username=request.username,
            email=request.email,
            message=f"User registered successfully. {'Verification email sent.' if request.send_verification_email else ''}"
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to register user: {e}")
        if "already exists" in str(e).lower():
            raise BadRequestException(str(e))
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@sso_router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(
    request: TokenRefreshRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh SSO access token using refresh token.
    
    This endpoint allows users to refresh their session token using
    the refresh token obtained during initial authentication.
    """
    registry = get_plugin_registry()
    redis_client = await get_redis_client()
    
    # Validate provider
    if request.provider not in registry.get_enabled_plugins():
        raise BadRequestException(f"Authentication provider not enabled: {request.provider}")
    
    # Get the plugin
    plugin = registry.get_plugin(request.provider)
    if not plugin:
        raise NotFoundException(f"Authentication provider not found: {request.provider}")
    
    try:
        # Use the plugin's refresh token method
        if hasattr(plugin, 'refresh_token'):
            auth_result = await plugin.refresh_token(request.refresh_token)
            
            if auth_result.status != AuthStatus.SUCCESS:
                raise UnauthorizedException(f"Token refresh failed: {auth_result.error_message}")
            
            # Get user info from the refreshed token
            user_info = auth_result.user_info
            if not user_info:
                raise BadRequestException("No user information received from provider")
            
            # Find the user account
            account = db.query(Account).filter(
                Account.provider == request.provider,
                Account.provider_account_id == user_info.provider_id
            ).first()
            
            if not account:
                raise NotFoundException("User account not found")
            
            user = account.user
            
            # Generate new API session token
            new_session_token = secrets.token_urlsafe(32)
            session_data = {
                "user_id": str(user.id),
                "account_id": str(account.id),
                "provider": request.provider,
                "username": user.username,
                "email": user.email,
                "created_at": str(datetime.now(timezone.utc)),
                "refreshed_at": str(datetime.now(timezone.utc))
            }
            
            # Store new session in Redis
            session_key = f"sso_session:{new_session_token}"
            await redis_client.set(
                session_key,
                json.dumps(session_data),
                ttl=86400  # 24 hours
            )
            
            # Update stored provider tokens if available
            if auth_result.access_token:
                token_key = f"sso_token:{request.provider}:{user.id}"
                token_data = {
                    "access_token": auth_result.access_token,
                    "refresh_token": auth_result.refresh_token,
                    "expires_at": str(auth_result.expires_at) if auth_result.expires_at else None
                }
                
                # Calculate expiration
                expiration = 3600  # Default 1 hour
                if auth_result.expires_at:
                    now = datetime.now(timezone.utc)
                    delta = auth_result.expires_at - now
                    expiration = max(int(delta.total_seconds()), 60)
                
                await redis_client.set(
                    token_key,
                    json.dumps(token_data),
                    ttl=expiration
                )
            
            return TokenRefreshResponse(
                access_token=new_session_token,
                expires_in=86400,  # 24 hours for our session token
                refresh_token=auth_result.refresh_token  # New refresh token if provider rotates them
            )
            
        else:
            raise BadRequestException(f"Token refresh not supported by provider: {request.provider}")
            
    except UnauthorizedException:
        raise
    except Exception as e:
        logger.error(f"Failed to refresh token: {e}")
        raise HTTPException(status_code=500, detail=f"Token refresh failed: {str(e)}")
