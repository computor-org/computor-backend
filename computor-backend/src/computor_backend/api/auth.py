"""
Authentication API endpoints for SSO authentication.

This module provides:
- SSO/OAuth authentication with multiple providers (Keycloak, GitLab, etc.)
- Token refresh and logout functionality
"""

import json
import logging
import secrets
from typing import List, Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from computor_backend.database import get_db
from computor_backend.permissions.auth import get_current_principal
from computor_backend.exceptions import (
    UnauthorizedException,
    BadRequestException,
    NotFoundException,
)
from computor_backend.permissions.principal import Principal
from computor_backend.plugins import PluginMetadata
from computor_backend.plugins.registry import get_plugin_registry
from computor_backend.redis_cache import get_redis_client
from computor_types.auth import (
    LogoutResponse,
    LocalTokenRefreshRequest,
    LocalTokenRefreshResponse,
    ProviderInfo,
    LoginRequest,
    TokenRefreshRequest,
    TokenRefreshResponse,
    GitLabRegisterRequest,
    GitLabRegisterResponse,
)

logger = logging.getLogger(__name__)

auth_router = APIRouter(prefix="/auth")

@auth_router.get("/providers", response_model=List[ProviderInfo])
async def list_providers() -> List[ProviderInfo]:
    """
    List available authentication providers.

    Returns all enabled authentication providers with their metadata.
    """
    registry = get_plugin_registry()
    providers = []

    for plugin_name in registry.get_enabled_plugins():
        metadata = registry.get_plugin_metadata(plugin_name)
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

    # Check if provider exists and is enabled
    if provider not in registry.get_enabled_plugins():
        raise NotFoundException(f"Authentication provider not found or not enabled: {provider}")

    # If the plugin is enabled but not yet loaded (e.g. Keycloak wasn't ready at startup), try now
    if registry.get_plugin(provider) is None:
        try:
            await registry.load_builtin_provider(provider)
            logger.info(f"Lazily loaded provider: {provider}")
        except Exception as e:
            logger.warning(f"Could not lazily load provider {provider}: {e}")

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
    
    # X-Forwarded-Proto is set by nginx (SSL terminator). Replace the scheme
    # so the callback URI sent to Keycloak uses https, not http.
    callback_url = str(request.url_for("handle_callback", provider=provider))
    proto = request.headers.get("x-forwarded-proto")
    if proto:
        callback_url = callback_url.replace(f"{request.url.scheme}://", f"{proto}://", 1)

    try:
        # Get login URL from provider
        login_url = registry.get_login_url(provider, callback_url, state)
        
        # Redirect to provider login
        return RedirectResponse(url=login_url, status_code=302)
        
    except Exception as e:
        logger.error(f"Failed to initiate login for {provider}: {e}")
        logger.error(f"Exception type: {type(e)}")
        logger.error(f"Exception traceback:", exc_info=True)
        from computor_backend.exceptions import InternalServerException
        raise InternalServerException(detail=f"Failed to initiate login: {str(e)}") from e

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
        callback_url = str(request.url_for("handle_callback", provider=provider))
        proto = request.headers.get("x-forwarded-proto")
        if proto:
            callback_url = callback_url.replace(f"{request.url.scheme}://", f"{proto}://", 1)

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

        # Set the same HttpOnly cookies as the local /login flow so the frontend
        # can authenticate to /user with credentials: 'include' after redirect.
        redirect_response = RedirectResponse(url=redirect_url, status_code=302)
        redirect_response.set_cookie(
            key="ct_access_token",
            value=result["token"],
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
            max_age=3600,
        )
        redirect_response.set_cookie(
            key="ct_refresh_token",
            value=result["refresh_token"],
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=604800,
        )
        return redirect_response

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


@auth_router.get("/{provider}/logout", name="sso_logout")
async def sso_logout(
    provider: str,
    request: Request,
    post_logout_redirect_uri: Optional[str] = Query(None),
    cache=Depends(get_redis_client),
) -> RedirectResponse:
    """
    SSO logout: clears the backend session cookies AND ends the Keycloak SSO
    session by redirecting the browser to the provider's end_session_endpoint.

    The frontend should navigate to this URL (browser redirect, not XHR) so
    the cookie-clearing + Keycloak end-session flow completes properly.

    Designed to be tolerant of an already-expired or missing local session —
    we always clear cookies and forward to Keycloak so the user is fully
    signed out at the IdP.
    """
    import os
    from computor_backend.utils.token_hash import hash_token

    current_token = request.cookies.get("ct_access_token")
    refresh_token = request.cookies.get("ct_refresh_token")

    # Read the stored id_token (for id_token_hint) before deleting the session,
    # then best-effort cleanup of Redis sessions — don't fail logout if Redis is unhappy.
    id_token_hint = None
    try:
        if current_token:
            session_key = f"sso_session:{hash_token(current_token)}"
            raw = await cache.get(session_key)
            if raw:
                try:
                    id_token_hint = json.loads(raw).get("id_token")
                except Exception:
                    pass
            await cache.delete(session_key)
        if refresh_token:
            await cache.delete(f"sso_session:{hash_token(refresh_token)}")
    except Exception as e:
        logger.warning(f"Redis session cleanup failed during SSO logout: {e}")

    registry = get_plugin_registry()
    plugin = registry.get_plugin(provider)
    end_session_endpoint = None
    if plugin is not None and getattr(plugin, "_oidc_config", None):
        end_session_endpoint = plugin._oidc_config.get("end_session_endpoint")

    target = post_logout_redirect_uri or "/"
    if end_session_endpoint:
        params = {"client_id": os.environ.get("KEYCLOAK_CLIENT_ID", "computor-backend")}
        if post_logout_redirect_uri:
            params["post_logout_redirect_uri"] = post_logout_redirect_uri
        # id_token_hint lets Keycloak skip the "Do you want to log out?" prompt.
        if id_token_hint:
            params["id_token_hint"] = id_token_hint
        target = f"{end_session_endpoint}?{urlencode(params)}"

    redirect_response = RedirectResponse(url=target, status_code=302)
    redirect_response.delete_cookie(key="ct_access_token", samesite="lax")
    redirect_response.delete_cookie(key="ct_refresh_token", samesite="lax")
    return redirect_response

@auth_router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    response: Response,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    cache = Depends(get_redis_client)
) -> LogoutResponse:
    """
    Logout from current session.

    This endpoint works with any authentication type:
    - Local authentication (Bearer tokens)
    - SSO authentication (provider tokens)

    The Bearer token from the Authorization header will be invalidated.
    Cookies will also be cleared.
    """
    from computor_backend.business_logic.auth import logout_session

    # Extract token from Authorization header or cookie
    authorization = request.headers.get("Authorization")
    current_token = None

    if authorization and authorization.startswith("Bearer "):
        current_token = authorization.replace("Bearer ", "")
    else:
        # Try to get from cookie
        current_token = request.cookies.get("ct_access_token")

    result = await logout_session(
        access_token=current_token,
        principal=principal,
        db=db,
        cache=cache
    )

    # Clear cookies
    response.delete_cookie(key="ct_access_token", samesite="lax")
    response.delete_cookie(key="ct_refresh_token", samesite="lax")

    return result

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

@auth_router.post("/refresh/local", response_model=LocalTokenRefreshResponse)
async def refresh_local_token(
    request: LocalTokenRefreshRequest,
    db: Session = Depends(get_db),
    cache = Depends(get_redis_client)
) -> LocalTokenRefreshResponse:
    """
    Refresh local access token using refresh token.

    This endpoint allows users to refresh their session token for local
    (username/password) authentication using the refresh token obtained
    during initial login.

    Authentication is not required for this endpoint since the access token
    may be expired. The refresh token itself is validated to ensure security.
    """
    from computor_backend.business_logic.auth import refresh_local_token

    return await refresh_local_token(
        refresh_token=request.refresh_token,
        principal=None,  # Don't require authentication - refresh token is sufficient
        db=db,
        cache=cache
    )

@auth_router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(
    request: TokenRefreshRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db)
) -> TokenRefreshResponse:
    """
    Refresh SSO access token using refresh token.

    This endpoint allows users to refresh their session token using
    the refresh token obtained during initial SSO authentication.

    Requires authentication to ensure only the token owner can refresh it.
    """
    from computor_backend.business_logic.auth import refresh_sso_token

    result = await refresh_sso_token(
        refresh_token=request.refresh_token,
        provider=request.provider,
        principal=principal,
        db=db
    )

    return TokenRefreshResponse(**result)


@auth_router.get("/verify-coder-access")
async def verify_coder_access(
    request: Request,
    principal: Principal = Depends(get_current_principal)
) -> JSONResponse:
    """
    Traefik ForwardAuth endpoint for Coder workspace access control.

    This endpoint is called by Traefik before forwarding requests to code-server workspaces.
    It verifies that:
    1. The user is authenticated (via Bearer token, Basic auth, or API token)
    2. The authenticated user matches the user ID in the workspace URL

    URL Format: /coder/u{user_id}/{workspace_name}/...
    Example: /coder/u0232de59-e05d-4bc2-898f-b879c06/{workspace}/

    The 'u' prefix is required for Coder username compatibility, so we strip it to get the actual user ID.

    Returns:
    - 200 OK: User is authorized to access this workspace
    - 401 Unauthorized: User is not authenticated
    - 403 Forbidden: User is authenticated but not authorized for this workspace
    """
    import re

    # Get the original URI from Traefik headers
    original_uri = request.headers.get("X-Forwarded-Uri", request.url.path)

    # Debug: Log all headers to understand the authentication flow
    logger.info("=== ForwardAuth Debug ===")
    logger.info(f"ForwardAuth request for: {original_uri}")
    logger.info(f"Authenticated user: {principal.user_id}")
    logger.info("Headers received:")
    for header_name, header_value in request.headers.items():
        # Mask sensitive values
        if header_name.lower() in ["authorization", "cookie", "x-api-key"]:
            logger.info(f"  {header_name}: {header_value[:20]}..." if len(header_value) > 20 else f"  {header_name}: ***")
        else:
            logger.info(f"  {header_name}: {header_value}")
    logger.info("=========================")

    # Extract username from URL path: /coder/u{user_id}/{workspace}/...
    # Pattern: /coder/u<uuid>/<workspace>/*
    pattern = r"/coder/u([a-f0-9\-]+)/([^/]+)"
    match = re.match(pattern, original_uri)

    if not match:
        logger.warning(f"Invalid Coder URL format: {original_uri}")
        return JSONResponse(
            status_code=403,
            content={"detail": "Invalid workspace URL format"}
        )

    url_user_id = match.group(1)  # Extract user ID without 'u' prefix
    workspace_name = match.group(2)

    logger.debug(f"URL user_id: {url_user_id}, workspace: {workspace_name}")

    # Check if the authenticated user matches the workspace owner
    # Note: Coder may truncate usernames due to length limits, so we check if the
    # authenticated user ID starts with the URL user ID (which may be truncated)
    if not principal.user_id.startswith(url_user_id):
        logger.warning(
            f"User {principal.user_id} attempted to access workspace belonging to {url_user_id}"
        )
        return JSONResponse(
            status_code=403,
            content={
                "detail": "You are not authorized to access this workspace",
                "workspace_owner": url_user_id,
                "authenticated_user": principal.user_id
            }
        )

    # User is authorized
    logger.info(f"User {principal.user_id} authorized for workspace {workspace_name}")

    # Return 200 OK - Traefik will forward the request
    return JSONResponse(
        status_code=200,
        content={"status": "authorized", "user_id": principal.user_id, "workspace": workspace_name}
    )


@auth_router.post("/gitlab/register", response_model=GitLabRegisterResponse)
async def register_via_gitlab(
    request: GitLabRegisterRequest,
    db: Session = Depends(get_db),
) -> GitLabRegisterResponse:
    """Provision (or reset) a user's Keycloak login using a GitLab PAT as proof.

    Idempotent by design: if the Keycloak user already exists, its password is
    reset — so a user who forgot their credentials simply re-runs this with a
    new password. The Keycloak account links to the existing computor user on
    first SSO login via the email match in handle_sso_callback.
    """
    from computor_backend.business_logic.auth import (
        verify_user_with_gitlab_pat,
        find_or_create_gitlab_account,
        provision_keycloak_login,
    )

    # 1. Prove identity. Matches the GitLab-profile email against User.email or
    #    the org-scoped StudentProfile.student_email; raises if no match.
    user, gitlab_url, gitlab_user_data = await verify_user_with_gitlab_pat(
        access_token=request.gitlab_pat,
        gitlab_url=request.gitlab_url,
        db=db,
    )

    if not user.email:
        raise BadRequestException("Verified user has no email on record; cannot provision Keycloak login.")

    # 2. Create or reset the Keycloak login (PAT was the authorization proof).
    email = user.email
    kc_user_id, created = await provision_keycloak_login(
        email=email,
        password=request.new_password,
        given_name=user.given_name,
        family_name=user.family_name,
    )

    # 3. Link the GitLab account (PAT is not stored).
    await find_or_create_gitlab_account(
        user=user,
        gitlab_url=gitlab_url,
        gitlab_user_data=gitlab_user_data,
        db=db,
    )

    logger.info(
        f"GitLab-PAT Keycloak provisioning for {email} "
        f"(user {user.id}, kc {kc_user_id}, created={created})"
    )
    return GitLabRegisterResponse(user_id=str(user.id), email=email, created=created)
