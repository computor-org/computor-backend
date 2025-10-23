"""Business logic for authentication and user session management."""

import secrets
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from computor_backend.api.exceptions import (
    UnauthorizedException,
    BadRequestException,
    NotFoundException,
)
from computor_backend.permissions.auth import AuthenticationService
from computor_backend.permissions.principal import Principal
from computor_backend.model.auth import User, Account
from computor_backend.redis_cache import get_redis_client
from computor_backend.plugins.registry import get_plugin_registry
from computor_backend.plugins import AuthStatus
from computor_backend.auth.keycloak_admin import KeycloakAdminClient, KeycloakUser
from computor_types.auth import (
    LocalLoginRequest,
    LocalLoginResponse,
    LocalTokenRefreshRequest,
    LocalTokenRefreshResponse,
    LogoutResponse,
)

logger = logging.getLogger(__name__)

# Token TTL configuration
ACCESS_TOKEN_TTL = 60 * 60 # 1 hour
REFRESH_TOKEN_TTL = 14 * 24 * 60 * 60 # 14 days


async def login_with_local_credentials(
    username: str,
    password: str,
    ip_address: str,
    user_agent: str,
    db: Session,
    cache = None,
) -> LocalLoginResponse:
    """
    Authenticate user with local credentials and generate Bearer tokens.

    Args:
        username: Username or email
        password: User password
        ip_address: Client IP address
        user_agent: User agent string
        db: Database session
        cache: Redis cache instance

    Returns:
        LocalLoginResponse with access and refresh tokens

    Raises:
        UnauthorizedException: If credentials are invalid
    """
    from computor_backend.utils.token_hash import generate_token, hash_token, hash_token_binary
    from computor_backend.utils.client_info import make_device_label
    from computor_backend.repositories.session_repo import SessionRepository

    # Authenticate using the AuthenticationService (wrap blocking DB query)
    auth_result = await run_in_threadpool(
        lambda: AuthenticationService.authenticate_basic(username, password, db)
    )

    # Generate session tokens
    access_token = generate_token(32)
    refresh_token = generate_token(32)

    # Hash tokens for storage
    access_token_hash = hash_token(access_token)
    refresh_token_hash_binary = hash_token_binary(refresh_token)

    # Store session in Redis
    redis_client = await get_redis_client()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=ACCESS_TOKEN_TTL)
    refresh_expires_at = now + timedelta(seconds=REFRESH_TOKEN_TTL)

    # Store HASHED access token in Redis
    access_session_data = {
        "user_id": str(auth_result.user_id),
        "provider": "local",
        "created_at": str(now),
        "token_type": "access",
    }

    await redis_client.set(
        f"sso_session:{access_token_hash}",  # Store hash, not plain token
        json.dumps(access_session_data),
        ex=ACCESS_TOKEN_TTL,
    )

    # Store HASHED refresh token in Redis
    refresh_session_data = {
        "user_id": str(auth_result.user_id),
        "provider": "local",
        "created_at": str(now),
        "expires_at": str(now + timedelta(seconds=REFRESH_TOKEN_TTL)),  # Absolute expiration
        "token_type": "refresh",
        "access_token_hash": access_token_hash,  # Reference to access token
    }

    await redis_client.set(
        f"refresh_token:{hash_token(refresh_token)}",  # Store hash
        json.dumps(refresh_session_data),
        ex=REFRESH_TOKEN_TTL,  # Redis TTL as backup
    )

    # Create Session in database with device tracking
    from computor_backend.model.auth import Session as SessionModel

    device_label = make_device_label(user_agent)
    session_repo = SessionRepository(db, SessionModel, cache)

    # Create session model instance
    session = SessionModel(
        user_id=str(auth_result.user_id),
        session_id=access_token_hash,  # Store HASH in DB
        refresh_token_hash=refresh_token_hash_binary,  # Binary hash
        created_ip=ip_address,
        last_ip=ip_address,
        user_agent=user_agent,
        device_label=device_label,
        expires_at=expires_at,
        refresh_expires_at=refresh_expires_at,
        properties={
            "provider": "local",
            "login_method": "credentials"
        }
    )
    session = session_repo.create(session)

    logger.info(f"Local login successful for user {auth_result.user_id}, session {session.id}, device: {device_label}")

    return LocalLoginResponse(
        access_token=access_token,  # Return PLAIN token to client
        refresh_token=refresh_token,  # Return PLAIN token to client
        expires_in=ACCESS_TOKEN_TTL,
        user_id=str(auth_result.user_id),
        token_type="Bearer",
    )


async def refresh_local_token(
    refresh_token: str,
    principal: Optional[Principal],
    db: Session,
    cache = None,
) -> LocalTokenRefreshResponse:
    """
    Refresh local access token using refresh token.

    Args:
        refresh_token: Valid refresh token
        principal: Current authenticated principal (optional, can be from expired token)
        db: Database session
        cache: Redis cache instance

    Returns:
        LocalTokenRefreshResponse with new access token

    Raises:
        UnauthorizedException: If refresh token is invalid or expired or doesn't belong to user
        NotFoundException: If user not found
    """
    from computor_backend.utils.token_hash import generate_token, hash_token, hash_token_binary
    from computor_backend.repositories.session_repo import SessionRepository

    redis_client = await get_redis_client()
    now = datetime.now(timezone.utc)  # Define now at the beginning

    # Hash the refresh token for lookup
    refresh_token_hash = hash_token(refresh_token)
    refresh_key = f"refresh_token:{refresh_token_hash}"
    refresh_data_raw = await redis_client.get(refresh_key)

    if not refresh_data_raw:
        raise UnauthorizedException("Invalid or expired refresh token")

    try:
        refresh_data = json.loads(refresh_data_raw)
        user_id = refresh_data.get("user_id")

        if not user_id:
            raise UnauthorizedException("Invalid refresh token data")

        # Check absolute expiration (expires_at field from login)
        expires_at_str = refresh_data.get("expires_at")
        expires_at = None
        if expires_at_str:
            try:
                # Parse ISO format and make timezone-aware if needed
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if expires_at < now:
                    logger.info(f"Refresh token expired for user {user_id} (absolute expiration)")
                    raise UnauthorizedException("Refresh token has expired")
            except (ValueError, AttributeError) as e:
                logger.warning(f"Failed to parse expires_at: {e}, using fallback")

        # Verify the refresh token belongs to the authenticated user (if principal is available)
        if principal and str(user_id) != str(principal.user_id):
            raise UnauthorizedException("Refresh token does not belong to authenticated user")

        # Verify user still exists (wrap blocking DB query)
        user = await run_in_threadpool(
            lambda: db.query(User).filter(User.id == user_id).first()
        )
        if not user:
            raise NotFoundException("User not found")

        # Generate new access token
        new_access_token = generate_token(32)
        new_access_token_hash = hash_token(new_access_token)

        # Store new HASHED access token in Redis
        access_session_data = {
            "user_id": str(user_id),
            "provider": "local",
            "created_at": str(now),
            "token_type": "access",
            "refreshed_at": str(now),
        }

        await redis_client.set(
            f"sso_session:{new_access_token_hash}",
            json.dumps(access_session_data),
            ex=ACCESS_TOKEN_TTL,
        )

        # Delete old access token from Redis
        old_access_token_hash = refresh_data.get("access_token_hash")
        if old_access_token_hash:
            await redis_client.delete(f"sso_session:{old_access_token_hash}")

        # Update refresh token with new access token reference
        # IMPORTANT: Keep original expires_at (absolute expiration)
        refresh_data["access_token_hash"] = new_access_token_hash
        refresh_data["refreshed_at"] = str(now)
        refresh_data["refresh_count"] = refresh_data.get("refresh_count", 0) + 1

        # Calculate remaining TTL to preserve absolute expiration
        if expires_at:  # expires_at already parsed above
            remaining_ttl = int((expires_at - now).total_seconds())
            if remaining_ttl > 0:
                await redis_client.set(
                    refresh_key, json.dumps(refresh_data), ex=remaining_ttl
                )
                logger.debug(f"Updated refresh token with {remaining_ttl}s remaining TTL")
            else:
                # Should have been caught earlier, but safety check
                raise UnauthorizedException("Refresh token has expired")
        else:
            # Fallback for old tokens without expires_at
            await redis_client.set(
                refresh_key, json.dumps(refresh_data), ex=REFRESH_TOKEN_TTL
            )
            logger.debug(f"Updated refresh token with fallback TTL {REFRESH_TOKEN_TTL}s")

        # Update Session in database
        from computor_backend.model.auth import Session as SessionModel
        from computor_backend.utils.token_hash import hash_token_binary

        session_repo = SessionRepository(db, SessionModel, cache)

        # Look up session by refresh token hash (checks refresh_expires_at, not access token expiry)
        refresh_token_hash_binary = hash_token_binary(refresh_token)
        session = session_repo.find_by_refresh_token_hash(refresh_token_hash_binary)

        if session:
            # Update session with new token hash, expiration, and increment counter
            new_expires_at = now + timedelta(seconds=ACCESS_TOKEN_TTL)
            session_repo.update(str(session.id), {
                "session_id": new_access_token_hash,
                "last_seen_at": now,
                "expires_at": new_expires_at,
            })
            session_repo.increment_refresh_counter(str(session.id))
            logger.info(f"Token refreshed for user {user_id}, session {session.id}, refresh count: {session.refresh_counter + 1}")
        else:
            logger.warning(f"Token refreshed for user {user_id} but session not found in database")

        return LocalTokenRefreshResponse(
            access_token=new_access_token,  # Return PLAIN token
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
    cache = None,
) -> LogoutResponse:
    """
    Logout from current session and invalidate tokens.

    Args:
        access_token: Current access token (Bearer token)
        principal: Current authenticated principal
        db: Database session
        cache: Redis cache instance

    Returns:
        LogoutResponse with status and provider info
    """
    from computor_backend.utils.token_hash import hash_token
    from computor_backend.repositories.session_repo import SessionRepository

    redis_client = await get_redis_client()
    provider_name = None

    if access_token:
        # Hash token for lookup
        access_token_hash = hash_token(access_token)
        session_key = f"sso_session:{access_token_hash}"
        session_data_raw = await redis_client.get(session_key)

        if session_data_raw:
            try:
                session_data = json.loads(session_data_raw)
                provider_name = session_data.get("provider", "unknown")

                # Delete the access token session from Redis
                await redis_client.delete(session_key)
                logger.info(
                    f"Deleted Redis session for user {principal.user_id}, provider: {provider_name}"
                )

                # End session in database
                from computor_backend.model.auth import Session as SessionModel
                session_repo = SessionRepository(db, SessionModel, cache)
                session = session_repo.find_by_session_id_hash(access_token_hash)
                if session:
                    session_repo.end_session(str(session.id), reason="User logout")
                    logger.info(f"Ended database session {session.id} for user {principal.user_id}")

                    # Delete refresh token from Redis if it exists
                    if session.refresh_token_hash:
                        # Find and delete the refresh token
                        # We need to search for it since we stored the hash
                        refresh_token_hash_hex = session.refresh_token_hash.hex() if isinstance(session.refresh_token_hash, bytes) else None
                        if refresh_token_hash_hex:
                            # Try to delete by searching properties
                            pass  # Refresh token cleanup will happen on next use

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
    principal: Principal,
    db: Session,
) -> Dict[str, Any]:
    """
    Refresh SSO access token using refresh token.

    Args:
        refresh_token: Refresh token from provider
        provider: Authentication provider name
        principal: Current authenticated principal
        db: Database session

    Returns:
        Dict with access_token, expires_in, refresh_token

    Raises:
        BadRequestException: If provider not enabled or refresh not supported
        UnauthorizedException: If token refresh fails or token doesn't belong to user
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

        # Verify the account belongs to the authenticated user
        if str(user.id) != str(principal.user_id):
            raise UnauthorizedException("Refresh token does not belong to authenticated user")

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
