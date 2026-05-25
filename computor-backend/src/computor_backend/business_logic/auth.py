"""Business logic for authentication and user session management."""

import secrets
import json
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import func
from starlette.concurrency import run_in_threadpool

from computor_backend.exceptions import (
    UnauthorizedException,
    BadRequestException,
    NotFoundException,
    ForbiddenException,
)
from computor_backend.permissions.auth import AuthenticationService
from computor_backend.permissions.principal import Principal
from computor_backend.model.auth import User, Account
from computor_backend.model.organization import Organization
from computor_backend.model.course import Course, CourseMember
from computor_backend.redis_cache import get_redis_client
from computor_backend.plugins.registry import get_plugin_registry
from computor_backend.plugins import AuthStatus
from computor_backend.auth.keycloak_admin import KeycloakAdminClient, KeycloakUser
from computor_types.auth import (
    LocalTokenRefreshRequest,
    LocalTokenRefreshResponse,
    LogoutResponse,
)

logger = logging.getLogger(__name__)


async def _provision_git_server_account(
    user_id: str,
    email: str,
    db: Session,
) -> None:
    """Record that this user has an account on the system git server.

    With OIDC, Forgejo/GitLab create the actual account on first login.
    This just ensures the Account row exists so the relationship is tracked.
    """
    from ..git_server.config import get_git_server_settings

    settings = get_git_server_settings()
    if not settings.enabled:
        return

    def _check_and_insert():
        existing = (
            db.query(Account)
            .filter(
                Account.provider == settings.git_server_url,
                Account.type == settings.git_server.lower(),
                Account.user_id == user_id,
            )
            .first()
        )
        if existing:
            return
        account = Account(
            provider=settings.git_server_url,
            type=settings.git_server.lower(),
            provider_account_id=email,
            user_id=user_id,
            properties={},
        )
        db.add(account)
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.warning(f"Failed to store git server Account for {email}: {e}")

    await run_in_threadpool(_check_and_insert)


# Token TTL configuration
ACCESS_TOKEN_TTL = 60 * 60 # 1 hour
REFRESH_TOKEN_TTL = 14 * 24 * 60 * 60 # 14 days


async def invalidate_principal_cache_for_token(token: str, cache):
    """
    Invalidate all Principal cache entries for a given token.

    This removes cached Principal objects to force re-authentication on next request.
    Useful when logging out or when user permissions change.

    Args:
        token: Access token (Bearer token)
        cache: Redis cache client
    """
    import hashlib

    try:
        # Invalidate all possible Principal cache keys for this token
        # These match the patterns in permissions/auth.py get_current_principal

        # Pattern 1: API token permissions
        api_key = hashlib.sha256(f"api_token_permissions:{token}".encode()).hexdigest()
        await cache.delete(api_key)
        logger.debug(f"Invalidated API token Principal cache: {api_key[:16]}...")

        # Pattern 2: SSO permissions
        sso_key = hashlib.sha256(f"sso_permissions:{token}".encode()).hexdigest()
        await cache.delete(sso_key)
        logger.debug(f"Invalidated SSO Principal cache: {sso_key[:16]}...")

    except Exception as e:
        logger.warning(f"Error invalidating Principal cache: {e}")


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

    # Invalidate Principal cache for this token
    if access_token:
        await invalidate_principal_cache_for_token(access_token, redis_client)
        logger.info(f"Invalidated Principal cache for user {principal.user_id} on logout")

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

            # Create new user — check for pre-existing user by email (e.g. from invite)
            user = (
                db.query(User).filter(User.email == user_info.email).first()
                if user_info.email
                else None
            )
            if user is None:
                user = User(
                    given_name=user_info.given_name or "",
                    family_name=user_info.family_name or "",
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

        # Bootstrap _admin from the Keycloak "administrators" group.
        # Additive only: membership grants _admin, but we never revoke — admin
        # can also be granted manually in the computor DB, which stays authoritative.
        groups = user_info.groups or []
        is_kc_admin = any(g.strip("/").split("/")[-1] == "administrators" for g in groups)
        if is_kc_admin:
            from computor_backend.model.role import UserRole
            existing_admin = (
                db.query(UserRole)
                .filter(UserRole.user_id == user.id, UserRole.role_id == "_admin")
                .first()
            )
            if not existing_admin:
                db.add(UserRole(user_id=user.id, role_id="_admin"))

        # Capture primitives before commit — attributes expire after commit
        user_primitives = {
            "id": str(user.id),
            "account_id": str(account.id),
            "email": user.email,
            "given_name": user.given_name,
            "family_name": user.family_name,
        }
        db.commit()
        return is_new_user, user_primitives

    is_new_user, user_primitives = await run_in_threadpool(_find_or_create_account)

    await _provision_git_server_account(
        user_id=user_primitives["id"],
        email=user_primitives["email"],
        db=db,
    )

    # Generate API session token for the user
    api_session_token = secrets.token_urlsafe(32)
    session_data = {
        "user_id": user_primitives["id"],
        "account_id": user_primitives["account_id"],
        "provider": provider,
        "email": user_primitives["email"],
        "created_at": str(datetime.now(timezone.utc)),
        # Stored so /auth/{provider}/logout can pass id_token_hint to Keycloak
        # and skip its logout-confirmation prompt.
        "id_token": (auth_result.session_data or {}).get("id_token"),
    }

    # Store session in Redis with TTL. authenticate_sso() in permissions/auth.py
    # looks up the session by the HASH of the token, not the plain token, so
    # we must store the hash (matching the local /login flow).
    from computor_backend.utils.token_hash import hash_token
    session_key = f"sso_session:{hash_token(api_session_token)}"
    await redis_client.set(session_key, json.dumps(session_data), ex=86400)  # 24 hours

    # Store tokens in Redis if available
    if auth_result.access_token:
        token_key = f"sso_token:{provider}:{user_primitives['id']}"
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
        "user_id": user_primitives["id"],
        "account_id": user_primitives["account_id"],
        "token": api_session_token,
        "refresh_token": auth_result.refresh_token if auth_result.refresh_token else "",
        "is_new_user": is_new_user,
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
            "email": user.email,
            "created_at": str(datetime.now(timezone.utc)),
            "refreshed_at": str(datetime.now(timezone.utc)),
        }

        # Store new session in Redis — keyed by token HASH to match authenticate_sso() lookup.
        from computor_backend.utils.token_hash import hash_token
        session_key = f"sso_session:{hash_token(new_session_token)}"
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


async def verify_user_with_gitlab_pat(
    access_token: str,
    gitlab_url: str,
    db: Session,
) -> Tuple[User, str, Dict[str, Any]]:
    """
    Verify user identity via GitLab Personal Access Token.

    This function verifies that:
    1. The provided token is a valid Personal Access Token (not bot/project/group token)
    2. Fetches the email from GitLab user profile
    3. Finds user in our system with matching email
    4. Verifies user belongs to an organization that uses the specified GitLab instance

    Args:
        access_token: GitLab Personal Access Token (glpat-...)
        gitlab_url: GitLab instance URL (e.g., https://gitlab.com)
        db: Database session

    Returns:
        Tuple of (User, gitlab_url_used, gitlab_user_data)

    Raises:
        NotFoundException: If user not found
        ForbiddenException: If user not in GitLab-enabled org
        BadRequestException: If token is not a personal access token
        UnauthorizedException: If GitLab authentication fails

    Security Notes:
        - GLPAT is NOT stored (GDPR/DSGVO compliance)
        - Only used for verification
        - Account entry is created to link user to GitLab
    """
    from gitlab import Gitlab
    from gitlab.exceptions import GitlabAuthenticationError, GitlabGetError

    # 1. Authenticate with GitLab and fetch user info
    try:
        logger.info(f"Attempting GitLab authentication at {gitlab_url}")

        # Create GitLab client
        gl = Gitlab(gitlab_url, private_token=access_token)
        gl.auth()

        # Get current user info from GitLab
        gitlab_user = gl.user

        # 2. Verify it's a personal access token (not bot/project/group token)
        if not hasattr(gitlab_user, 'email') or not gitlab_user.email:
            raise BadRequestException(
                "This token does not appear to be a Personal Access Token. "
                "Project and group access tokens are not allowed. "
                "Please create a Personal Access Token in your GitLab user settings."
            )

        if hasattr(gitlab_user, 'bot') and gitlab_user.bot:
            raise BadRequestException(
                "Bot tokens are not allowed. Please use a Personal Access Token."
            )

        gitlab_email = gitlab_user.email
        logger.info(f"Successfully authenticated with GitLab. User email: {gitlab_email}")

    except GitlabAuthenticationError as e:
        raise UnauthorizedException(f"GitLab authentication failed: {str(e)}") from e
    except GitlabGetError as e:
        raise UnauthorizedException(f"GitLab API error: {str(e)}") from e
    except (BadRequestException,):
        # Re-raise our own validation errors
        raise
    except Exception as e:
        logger.error(f"Unexpected error with GitLab: {str(e)}", exc_info=True)
        raise UnauthorizedException(f"Failed to verify GitLab token: {str(e)}") from e

    # 3. Find user in our system by email (case-insensitive)
    # Try User.email first - if found, user can link any GitLab instance
    from computor_backend.model.auth import StudentProfile

    user = db.query(User).filter(User.email == gitlab_email.lower()).first()

    if user:
        logger.info(f"Found user {user.email} (ID: {user.id}) by User.email")
    else:
        # If not found by User.email, try StudentProfile.student_email
        # Join with Organization and filter by GitLab URL in the query
        from computor_backend.model.organization import Organization

        # Normalize GitLab URL (remove trailing slash if present)
        normalized_gitlab_url = gitlab_url.rstrip('/')

        student_profile = (
            db.query(StudentProfile)
            .join(Organization, StudentProfile.organization_id == Organization.id)
            .filter(
                StudentProfile.student_email == gitlab_email.lower(),
                Organization.properties["gitlab"].op("->>")("url") == normalized_gitlab_url
            )
            .first()
        )

        if student_profile:
            user = student_profile.user
            logger.info(
                f"Found user {user.email} (ID: {user.id}) via StudentProfile.student_email "
                f"in organization {student_profile.organization_id}"
            )
        else:
            raise NotFoundException(
                f"No user found with email '{gitlab_email}' in any organization using {gitlab_url}"
            )

    logger.info(f"Successfully verified user {user.email} (ID: {user.id}) with GitLab email {gitlab_email}")

    # 5. Return user and GitLab info
    gitlab_user_data = {
        'id': gitlab_user.id,
        'username': gitlab_user.username,
        'email': gitlab_user.email,
        'name': gitlab_user.name,
    }

    logger.info(
        f"Successfully verified user {user.email} via GitLab PAT "
        f"(GitLab user: {gitlab_user.username}, instance: {gitlab_url})"
    )

    return user, gitlab_url, gitlab_user_data


async def find_or_create_gitlab_account(
    user: User,
    gitlab_url: str,
    gitlab_user_data: Dict[str, Any],
    db: Session,
) -> Account:
    """
    Find existing or create new GitLab account entry for user.

    This links the user to their GitLab account for future reference.
    Note: GLPAT is NOT stored here (GDPR/DSGVO compliance).

    Args:
        user: User object
        gitlab_url: GitLab instance URL
        gitlab_user_data: GitLab user information (id, username, email, name)
        db: Database session

    Returns:
        Account object (existing or newly created)
    """
    def _find_or_create():
        # Try to find existing account using CORRECT schema pattern:
        # - provider = GitLab URL
        # - type = "gitlab"
        # - provider_account_id = GitLab username
        account = (
            db.query(Account)
            .filter(
                Account.provider == gitlab_url,
                Account.type == "gitlab",
                Account.provider_account_id == gitlab_user_data['username'],
                Account.user_id == user.id,
            )
            .first()
        )

        if account:
            # Update account properties with latest info
            account.properties = {
                "gitlab_user_id": str(gitlab_user_data['id']),
                "email": gitlab_user_data['email'],
                "name": gitlab_user_data['name'],
                "last_verified": str(datetime.now(timezone.utc)),
            }
            logger.info(f"Updated existing GitLab account for user {user.email}")
        else:
            # Create new account using CORRECT schema pattern
            account = Account(
                provider=gitlab_url,
                type="gitlab",
                provider_account_id=gitlab_user_data['username'],
                user_id=user.id,
                properties={
                    "gitlab_user_id": str(gitlab_user_data['id']),
                    "email": gitlab_user_data['email'],
                    "name": gitlab_user_data['name'],
                    "created_via": "gitlab_pat_verification",
                    "first_verified": str(datetime.now(timezone.utc)),
                },
            )
            db.add(account)
            logger.info(f"Created new GitLab account for user {user.email}")

        db.commit()
        db.refresh(account)
        return account

    return await run_in_threadpool(_find_or_create)
