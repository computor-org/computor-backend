"""Business logic for authentication and user session management."""

import secrets
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from ctutor_backend.api.exceptions import (
    UnauthorizedException,
    BadRequestException,
    NotFoundException,
)
from ctutor_backend.permissions.auth import AuthenticationService
from ctutor_backend.permissions.principal import Principal
from ctutor_backend.model.auth import User, Account
from ctutor_backend.redis_cache import get_redis_client
from ctutor_backend.plugins.registry import get_plugin_registry
from ctutor_backend.plugins import AuthStatus
from ctutor_backend.auth.keycloak_admin import KeycloakAdminClient, KeycloakUser
from ctutor_backend.interface.auth import (
    LocalLoginRequest,
    LocalLoginResponse,
    LocalTokenRefreshRequest,
    LocalTokenRefreshResponse,
    LogoutResponse,
)

logger = logging.getLogger(__name__)

# Token TTL configuration
ACCESS_TOKEN_TTL = 86400  # 24 hours
REFRESH_TOKEN_TTL = 604800  # 7 days


async def login_with_local_credentials(
    username: str,
    password: str,
    db: Session,
) -> LocalLoginResponse:
    """
    Authenticate user with local credentials and generate Bearer tokens.

    Args:
        username: Username or email
        password: User password
        db: Database session

    Returns:
        LocalLoginResponse with access and refresh tokens

    Raises:
        UnauthorizedException: If credentials are invalid
    """
    # Authenticate using the AuthenticationService (wrap blocking DB query)
    auth_result = await run_in_threadpool(
        lambda: AuthenticationService.authenticate_basic(username, password, db)
    )

    # Generate session tokens
    access_token = secrets.token_urlsafe(32)
    refresh_token = secrets.token_urlsafe(32)

    # Store session in Redis
    redis_client = await get_redis_client()

    # Store access token session
    access_session_data = {
        "user_id": str(auth_result.user_id),
        "provider": "local",
        "created_at": str(datetime.now(timezone.utc)),
        "token_type": "access",
    }

    await redis_client.set(
        f"sso_session:{access_token}",
        json.dumps(access_session_data),
        ex=ACCESS_TOKEN_TTL,
    )

    # Store refresh token session
    refresh_session_data = {
        "user_id": str(auth_result.user_id),
        "provider": "local",
        "created_at": str(datetime.now(timezone.utc)),
        "token_type": "refresh",
        "access_token": access_token,
    }

    await redis_client.set(
        f"refresh_token:{refresh_token}",
        json.dumps(refresh_session_data),
        ex=REFRESH_TOKEN_TTL,
    )

    logger.info(f"Local login successful for user {auth_result.user_id}")

    return LocalLoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_TTL,
        user_id=str(auth_result.user_id),
        token_type="Bearer",
    )


async def refresh_local_token(
    refresh_token: str,
    db: Session,
) -> LocalTokenRefreshResponse:
    """
    Refresh local access token using refresh token.

    Args:
        refresh_token: Valid refresh token
        db: Database session

    Returns:
        LocalTokenRefreshResponse with new access token

    Raises:
        UnauthorizedException: If refresh token is invalid or expired
        NotFoundException: If user not found
    """
    redis_client = await get_redis_client()

    # Get refresh token data from Redis
    refresh_key = f"refresh_token:{refresh_token}"
    refresh_data_raw = await redis_client.get(refresh_key)

    if not refresh_data_raw:
        raise UnauthorizedException("Invalid or expired refresh token")

    try:
        refresh_data = json.loads(refresh_data_raw)
        user_id = refresh_data.get("user_id")

        if not user_id:
            raise UnauthorizedException("Invalid refresh token data")

        # Verify user still exists (wrap blocking DB query)
        user = await run_in_threadpool(
            lambda: db.query(User).filter(User.id == user_id).first()
        )
        if not user:
            raise NotFoundException("User not found")

        # Generate new access token
        new_access_token = secrets.token_urlsafe(32)

        # Store new access token session
        access_session_data = {
            "user_id": str(user_id),
            "provider": "local",
            "created_at": str(datetime.now(timezone.utc)),
            "token_type": "access",
            "refreshed_at": str(datetime.now(timezone.utc)),
        }

        await redis_client.set(
            f"sso_session:{new_access_token}",
            json.dumps(access_session_data),
            ex=ACCESS_TOKEN_TTL,
        )

        # Update the old access token reference in refresh token if it exists
        old_access_token = refresh_data.get("access_token")
        if old_access_token:
            # Delete old access token
            await redis_client.delete(f"sso_session:{old_access_token}")

        # Update refresh token with new access token reference
        refresh_data["access_token"] = new_access_token
        refresh_data["refreshed_at"] = str(datetime.now(timezone.utc))

        await redis_client.set(
            refresh_key, json.dumps(refresh_data), ex=REFRESH_TOKEN_TTL
        )

        logger.info(f"Token refreshed for user {user_id}")

        return LocalTokenRefreshResponse(
            access_token=new_access_token,
            expires_in=ACCESS_TOKEN_TTL,
            refresh_token=refresh_token,  # Same refresh token
            token_type="Bearer",
        )

    except json.JSONDecodeError:
        raise UnauthorizedException("Invalid refresh token format")


async def logout_session(
    access_token: Optional[str],
    principal: Principal,
    db: Session,
) -> LogoutResponse:
    """
    Logout from current session and invalidate tokens.

    Args:
        access_token: Current access token (Bearer token)
        principal: Current authenticated principal
        db: Database session

    Returns:
        LogoutResponse with status and provider info
    """
    redis_client = await get_redis_client()
    provider_name = None

    if access_token:
        # Check if this is a local session token
        session_key = f"sso_session:{access_token}"
        session_data_raw = await redis_client.get(session_key)

        if session_data_raw:
            try:
                session_data = json.loads(session_data_raw)
                provider_name = session_data.get("provider", "unknown")

                # Delete the access token session
                await redis_client.delete(session_key)
                logger.info(
                    f"Deleted session for user {principal.user_id}, provider: {provider_name}"
                )

            except json.JSONDecodeError:
                logger.warning("Failed to parse session data during logout")

        # Also check for SSO provider tokens
        if principal.user_id:
            # Try to delete provider-specific tokens for all known providers
            registry = get_plugin_registry()
            for provider in registry.get_enabled_plugins():
                token_key = f"sso_token:{provider}:{principal.user_id}"
                token_data_raw = await redis_client.get(token_key)

                if token_data_raw:
                    try:
                        token_data = json.loads(token_data_raw)
                        access_token_provider = token_data.get("access_token")

                        if access_token_provider:
                            # Perform provider logout
                            plugin = registry.get_plugin(provider)
                            if plugin and hasattr(plugin, "logout"):
                                try:
                                    await plugin.logout(access_token_provider)
                                    logger.info(f"Performed provider logout for {provider}")
                                except Exception as e:
                                    logger.error(f"Failed to logout from {provider}: {e}")

                        # Delete stored tokens
                        await redis_client.delete(token_key)
                        provider_name = provider
                    except Exception as e:
                        logger.error(
                            f"Error processing provider tokens during logout: {e}"
                        )

    return LogoutResponse(message="Logout successful", provider=provider_name)


async def handle_sso_callback(
    provider: str,
    code: str,
    state: Optional[str],
    state_data: Dict[str, Any],
    callback_url: str,
    db: Session,
) -> Dict[str, Any]:
    """
    Handle OAuth callback from SSO provider.

    Args:
        provider: Provider name
        code: Authorization code
        state: State parameter
        state_data: Validated state data from Redis
        callback_url: Callback URL
        db: Database session

    Returns:
        Dict with user_id, account_id, token, refresh_token, is_new_user

    Raises:
        UnauthorizedException: If authentication fails
        BadRequestException: If user info missing
    """
    registry = get_plugin_registry()
    redis_client = await get_redis_client()

    # Handle callback with provider
    auth_result = await registry.handle_callback(provider, code, state, callback_url)

    if auth_result.status != AuthStatus.SUCCESS:
        raise UnauthorizedException(
            f"Authentication failed: {auth_result.error_message}"
        )

    # Get user info
    user_info = auth_result.user_info
    if not user_info:
        raise BadRequestException("No user information received from provider")

    # Find or create user account (wrap blocking DB operations)
    def _find_or_create_account():
        nonlocal user_info, provider, registry

        account = (
            db.query(Account)
            .filter(
                Account.provider == provider,
                Account.type == registry.get_plugin_metadata(provider).provider_type.value,
                Account.provider_account_id == user_info.provider_id,
            )
            .first()
        )

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
                "last_login": (
                    str(auth_result.expires_at) if auth_result.expires_at else None
                ),
            }

        else:
            # New account - create user
            is_new_user = True

            # Create new user
            user = User(
                given_name=user_info.given_name or "",
                family_name=user_info.family_name or "",
                username=user_info.username
                or user_info.email
                or f"{provider}_{user_info.provider_id}",
                email=user_info.email,
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
                    "last_login": (
                        str(auth_result.expires_at) if auth_result.expires_at else None
                    ),
                },
            )
            db.add(account)

        db.commit()
        return user, account, is_new_user

    user, account, is_new_user = await run_in_threadpool(_find_or_create_account)

    # Generate API session token for the user
    api_session_token = secrets.token_urlsafe(32)
    session_data = {
        "user_id": str(user.id),
        "account_id": str(account.id),
        "provider": provider,
        "username": user.username,
        "email": user.email,
        "created_at": str(datetime.now(timezone.utc)),
    }

    # Store session in Redis with TTL
    session_key = f"sso_session:{api_session_token}"
    await redis_client.set(session_key, json.dumps(session_data), ex=86400)  # 24 hours

    # Store tokens in Redis if available
    if auth_result.access_token:
        token_key = f"sso_token:{provider}:{user.id}"
        token_data = {
            "access_token": auth_result.access_token,
            "refresh_token": auth_result.refresh_token,
            "expires_at": (
                str(auth_result.expires_at) if auth_result.expires_at else None
            ),
        }

        # Store with appropriate expiration
        expiration = 3600  # Default 1 hour
        if auth_result.expires_at:
            # Calculate seconds until expiration
            now = datetime.now(timezone.utc)
            delta = auth_result.expires_at - now
            expiration = max(int(delta.total_seconds()), 60)  # At least 1 minute

        await redis_client.set(token_key, json.dumps(token_data), ex=expiration)

    return {
        "user_id": str(user.id),
        "account_id": str(account.id),
        "token": api_session_token,
        "refresh_token": auth_result.refresh_token if auth_result.refresh_token else "",
        "is_new_user": is_new_user,
    }


async def register_sso_user(
    username: str,
    email: str,
    password: str,
    given_name: str,
    family_name: str,
    provider: str,
    send_verification_email: bool,
    db: Session,
) -> Dict[str, Any]:
    """
    Register a new user with SSO provider.

    Args:
        username: Username
        email: Email address
        password: Password
        given_name: First name
        family_name: Last name
        provider: Authentication provider
        send_verification_email: Whether to send verification email
        db: Database session

    Returns:
        Dict with user_id, provider_user_id, username, email, message

    Raises:
        BadRequestException: If provider not enabled or user exists
    """
    # Validate provider
    registry = get_plugin_registry()
    if provider not in registry.get_enabled_plugins():
        raise BadRequestException(f"Authentication provider not enabled: {provider}")

    # Check if user already exists in local database (wrap blocking query)
    existing_user = await run_in_threadpool(
        lambda: db.query(User)
        .filter((User.username == username) | (User.email == email))
        .first()
    )

    if existing_user:
        raise BadRequestException("User with this username or email already exists")

    # Create user in authentication provider
    if provider == "keycloak":
        keycloak_admin = KeycloakAdminClient()

        # Check if user exists in Keycloak
        if await keycloak_admin.user_exists(username):
            raise BadRequestException("User already exists in Keycloak")

        # Create Keycloak user
        keycloak_user = KeycloakUser(
            username=username,
            email=email,
            firstName=given_name,
            lastName=family_name,
            enabled=True,
            emailVerified=False,
            credentials=[
                {"type": "password", "value": password, "temporary": False}
            ],
        )

        provider_user_id = await keycloak_admin.create_user(keycloak_user)

        # Send verification email if requested
        if send_verification_email and email:
            try:
                await keycloak_admin.send_verify_email(provider_user_id)
            except Exception as e:
                logger.warning(f"Failed to send verification email: {e}")
    else:
        raise BadRequestException(
            f"Registration not implemented for provider: {provider}"
        )

    # Create user in local database (wrap blocking DB operations)
    def _create_local_user():
        local_user = User(
            given_name=given_name,
            family_name=family_name,
            username=username,
            email=email,
        )
        db.add(local_user)
        db.flush()

        # Create account linking to provider
        account = Account(
            provider=provider,
            type="oidc",  # Keycloak uses OIDC
            provider_account_id=provider_user_id,
            user_id=local_user.id,
            properties={
                "email": email,
                "username": username,
                "registration_date": str(datetime.now(timezone.utc)),
            },
        )
        db.add(account)

        db.commit()
        return local_user

    local_user = await run_in_threadpool(_create_local_user)

    return {
        "user_id": str(local_user.id),
        "provider_user_id": provider_user_id,
        "username": username,
        "email": email,
        "message": f"User registered successfully. {'Verification email sent.' if send_verification_email else ''}",
    }


async def refresh_sso_token(
    refresh_token: str,
    provider: str,
    db: Session,
) -> Dict[str, Any]:
    """
    Refresh SSO access token using refresh token.

    Args:
        refresh_token: Refresh token from provider
        provider: Authentication provider name
        db: Database session

    Returns:
        Dict with access_token, expires_in, refresh_token

    Raises:
        BadRequestException: If provider not enabled or refresh not supported
        UnauthorizedException: If token refresh fails
        NotFoundException: If provider or account not found
    """
    registry = get_plugin_registry()
    redis_client = await get_redis_client()

    # Validate provider
    if provider not in registry.get_enabled_plugins():
        raise BadRequestException(f"Authentication provider not enabled: {provider}")

    # Get the plugin
    plugin = registry.get_plugin(provider)
    if not plugin:
        raise NotFoundException(f"Authentication provider not found: {provider}")

    # Use the plugin's refresh token method
    if hasattr(plugin, "refresh_token"):
        auth_result = await plugin.refresh_token(refresh_token)

        if auth_result.status != AuthStatus.SUCCESS:
            raise UnauthorizedException(
                f"Token refresh failed: {auth_result.error_message}"
            )

        # Get user info from the refreshed token
        user_info = auth_result.user_info
        if not user_info:
            raise BadRequestException("No user information received from provider")

        # Find the user account (wrap blocking query)
        account = await run_in_threadpool(
            lambda: db.query(Account)
            .filter(
                Account.provider == provider,
                Account.provider_account_id == user_info.provider_id,
            )
            .first()
        )

        if not account:
            raise NotFoundException("User account not found")

        user = account.user

        # Generate new API session token
        new_session_token = secrets.token_urlsafe(32)
        session_data = {
            "user_id": str(user.id),
            "account_id": str(account.id),
            "provider": provider,
            "username": user.username,
            "email": user.email,
            "created_at": str(datetime.now(timezone.utc)),
            "refreshed_at": str(datetime.now(timezone.utc)),
        }

        # Store new session in Redis
        session_key = f"sso_session:{new_session_token}"
        await redis_client.set(session_key, json.dumps(session_data), ex=86400)

        # Update stored provider tokens if available
        if auth_result.access_token:
            token_key = f"sso_token:{provider}:{user.id}"
            token_data = {
                "access_token": auth_result.access_token,
                "refresh_token": auth_result.refresh_token,
                "expires_at": (
                    str(auth_result.expires_at) if auth_result.expires_at else None
                ),
            }

            # Calculate expiration
            expiration = 3600  # Default 1 hour
            if auth_result.expires_at:
                now = datetime.now(timezone.utc)
                delta = auth_result.expires_at - now
                expiration = max(int(delta.total_seconds()), 60)

            await redis_client.set(token_key, json.dumps(token_data), ex=expiration)

        return {
            "access_token": new_session_token,
            "expires_in": 86400,  # 24 hours for our session token
            "refresh_token": (
                auth_result.refresh_token
            ),  # New refresh token if provider rotates them
        }

    else:
        raise BadRequestException(
            f"Token refresh not supported by provider: {provider}"
        )
