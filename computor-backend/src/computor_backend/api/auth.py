"""
Authentication API endpoints for both local and SSO authentication.

This module provides:
- Local username/password authentication with Bearer tokens
- SSO/OAuth authentication with multiple providers
- Token refresh and logout functionality
"""

import json
import logging
import secrets
from typing import List, Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from computor_backend.database import get_db
from computor_backend.permissions.auth import get_current_principal
from computor_backend.api.exceptions import (
    UnauthorizedException,
    BadRequestException,
    NotFoundException
)
from computor_backend.permissions.principal import Principal
from computor_backend.plugins import PluginMetadata
from computor_backend.plugins.registry import get_plugin_registry
from computor_backend.redis_cache import get_redis_client
from computor_types.auth import (
    LocalLoginRequest,
    LocalLoginResponse,
    LogoutResponse,
    LocalTokenRefreshRequest,
    LocalTokenRefreshResponse,
    ProviderInfo,
    LoginRequest,
    UserRegistrationRequest,
    UserRegistrationResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
)

logger = logging.getLogger(__name__)

auth_router = APIRouter(prefix="/auth")


@auth_router.post("/login", response_model=LocalLoginResponse)
async def login_with_credentials(
    request: LocalLoginRequest,
    db: Session = Depends(get_db)
) -> LocalLoginResponse:
    """
    Login with username and password to obtain Bearer tokens.

    This endpoint authenticates users with local credentials and returns
    access and refresh tokens that can be used for subsequent API requests.

    The access token should be included in the Authorization header as:
    `Authorization: Bearer <access_token>`
    """
    from computor_backend.business_logic.auth import login_with_local_credentials

    return await login_with_local_credentials(
        username=request.username,
        password=request.password,
        db=db
    )

@auth_router.get("/providers", response_model=List[ProviderInfo])
async def list_providers() -> List[ProviderInfo]:
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

@auth_router.get("/{provider}/login")
async def initiate_login(
    provider: str,
    redirect_uri: Optional[str] = Query(None, description="Redirect URI after authentication"),
    request: Request = None
) -> RedirectResponse:
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
    from computor_backend.redis_cache import get_redis_client
    redis_client = await get_redis_client()
    state_data = {
        "provider": provider,
        "redirect_uri": redirect_uri or str(request.url_for("sso_success")),
        "timestamp": str(request.headers.get("date", ""))
    }
    await redis_client.set(
        f"sso_state:{state}",
        json.dumps(state_data),
        ex=600  # 10 minutes
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
        from computor_backend.api.exceptions import InternalServerException
        raise InternalServerException(detail=f"Failed to initiate login: {str(e)}")

@auth_router.get("/{provider}/callback", name="handle_callback")
async def handle_callback(
    provider: str,
    code: str = Query(..., description="Authorization code"),
    state: Optional[str] = Query(None, description="State parameter"),
    request: Request = None,
    db: Session = Depends(get_db)
) -> RedirectResponse:
    """
    Handle OAuth callback from provider.

    Exchanges the authorization code for tokens and creates/updates user account.
    """
    from computor_backend.business_logic.auth import handle_sso_callback
    from computor_backend.redis_cache import get_redis_client

    redis_client = await get_redis_client()

    # Validate state parameter
    state_data = {}
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

        # Delegate to business logic
        result = await handle_sso_callback(
            provider=provider,
            code=code,
            state=state,
            state_data=state_data,
            callback_url=callback_url,
            db=db
        )

        # Get redirect URI from state or use default
        redirect_uri = state_data.get("redirect_uri", "/")

        # Redirect with encoded response
        params = {
            "user_id": result["user_id"],
            "account_id": result["account_id"],
            "is_new_user": str(result["is_new_user"]).lower(),
            "token": result["token"],
            "refresh_token": result["refresh_token"]
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

@auth_router.get("/success", name="sso_success")
async def sso_success():
    """Default success page after SSO authentication."""
    return {"message": "Authentication successful", "status": "success"}

@auth_router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db)
) -> LogoutResponse:
    """
    Logout from current session.

    This endpoint works with any authentication type:
    - Local authentication (Bearer tokens)
    - SSO authentication (provider tokens)

    The Bearer token from the Authorization header will be invalidated.
    """
    from computor_backend.business_logic.auth import logout_session

    # Extract token from Authorization header
    authorization = request.headers.get("Authorization")
    current_token = None

    if authorization and authorization.startswith("Bearer "):
        current_token = authorization.replace("Bearer ", "")

    return await logout_session(
        access_token=current_token,
        principal=principal,
        db=db
    )

@auth_router.get("/admin/plugins", dependencies=[Depends(get_current_principal)])
async def list_all_plugins(principal: Principal = Depends(get_current_principal)) -> dict:
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

@auth_router.post("/admin/plugins/{plugin_name}/enable", dependencies=[Depends(get_current_principal)])
async def enable_plugin(
    plugin_name: str,
    principal: Principal = Depends(get_current_principal)
) -> dict:
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

@auth_router.post("/admin/plugins/{plugin_name}/disable", dependencies=[Depends(get_current_principal)])
async def disable_plugin(
    plugin_name: str,
    principal: Principal = Depends(get_current_principal)
) -> dict:
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

@auth_router.post("/admin/plugins/reload", dependencies=[Depends(get_current_principal)])
async def reload_plugins(principal: Principal = Depends(get_current_principal)) -> dict:
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

@auth_router.post("/register", response_model=UserRegistrationResponse)
async def register_user(
    request: UserRegistrationRequest,
    db: Session = Depends(get_db)
) -> UserRegistrationResponse:
    """
    Register a new user with SSO provider.

    Creates user in both the authentication provider and local database.
    """
    from computor_backend.business_logic.auth import register_sso_user

    result = await register_sso_user(
        username=request.username,
        email=request.email,
        password=request.password,
        given_name=request.given_name,
        family_name=request.family_name,
        provider=request.provider,
        send_verification_email=request.send_verification_email,
        db=db
    )

    return UserRegistrationResponse(**result)

@auth_router.post("/refresh/local", response_model=LocalTokenRefreshResponse)
async def refresh_local_token(
    request: LocalTokenRefreshRequest,
    db: Session = Depends(get_db)
) -> LocalTokenRefreshResponse:
    """
    Refresh local access token using refresh token.

    This endpoint allows users to refresh their session token for local
    (username/password) authentication using the refresh token obtained
    during initial login.
    """
    from computor_backend.business_logic.auth import refresh_local_token

    return await refresh_local_token(
        refresh_token=request.refresh_token,
        db=db
    )

@auth_router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(
    request: TokenRefreshRequest,
    db: Session = Depends(get_db)
) -> TokenRefreshResponse:
    """
    Refresh SSO access token using refresh token.

    This endpoint allows users to refresh their session token using
    the refresh token obtained during initial SSO authentication.
    """
    from computor_backend.business_logic.auth import refresh_sso_token

    result = await refresh_sso_token(
        refresh_token=request.refresh_token,
        provider=request.provider,
        db=db
    )

    return TokenRefreshResponse(**result)
