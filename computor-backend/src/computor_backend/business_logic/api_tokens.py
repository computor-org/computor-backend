"""Business logic for API token management."""
import logging
from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from computor_backend.api.exceptions import (
    BadRequestException,
    NotFoundException,
    ForbiddenException,
)
from computor_backend.permissions.core import check_permissions
from computor_backend.permissions.principal import Principal
from computor_backend.model.service import ApiToken
from computor_backend.repositories import (
    ApiTokenRepository,
    ServiceRepository,
    ServiceTypeRepository,
    UserRepository,
)
from computor_backend.utils.api_token import generate_api_token
from computor_types.api_tokens import (
    ApiTokenCreate,
    ApiTokenAdminCreate,
    ApiTokenCreateResponse,
    ApiTokenGet,
    ApiTokenUpdate,
)

if TYPE_CHECKING:
    from computor_backend.cache import Cache

logger = logging.getLogger(__name__)

# Maximum retry attempts for token generation (collision handling)
MAX_TOKEN_GENERATION_RETRIES = 5

# Default scopes for service accounts based on service type category
# These scopes use the claim format: "resource:action"
DEFAULT_SERVICE_SCOPES = {
    "testing": [
        # Testing services need to read course data and create/update test results
        "course:get",
        "course:list",
        "course_content:get",
        "course_content:list",
        "course_content_type:get",
        "course_content_type:list",
        "submission_artifact:get",
        "submission_artifact:list",
        "submission_artifact:download",
        "result:get",
        "result:list",
        "result:create",
        "result:update",
        # Testing services need to download reference examples and their dependencies
        "example:get",
        "example:download",
    ],
    "worker": [
        # General workers need broader access for orchestration
        "course:get",
        "course:list",
        "course:create",
        "course:update",
        "course_content:get",
        "course_content:list",
        "organization:get",
        "organization:list",
    ],
    "review": [
        # Review services need to read content and create feedback
        "course_content:get",
        "course_content:list",
        "submission_artifact:get",
        "submission_artifact:list",
        "result:create",
    ],
    "integration": [
        # Integration services typically need read access
        "course:get",
        "course:list",
        "course_content:get",
        "course_content:list",
    ],
    "metrics": [
        # Metrics services need read-only access
        "course:get",
        "course:list",
        "result:get",
        "result:list",
    ],
}


def get_default_scopes_for_service(
    user_id: str,
    db: Session,
    cache: Optional["Cache"] = None,
) -> List[str]:
    """
    Get default scopes for a service account based on its service type.

    Args:
        user_id: Service user ID
        db: Database session
        cache: Optional cache for repository operations

    Returns:
        List of default scope strings, or empty list if not a service or no defaults
    """
    # Check if user is a service account
    user_repo = UserRepository(db, cache)
    user = user_repo.get_by_id_optional(user_id)
    if not user or not user.is_service:
        return []

    # Get the service record
    service_repo = ServiceRepository(db, cache)
    service = service_repo.find_by_user_id(user_id)
    if not service or not service.service_type_id:
        return []

    # Get the service type to determine category
    service_type_repo = ServiceTypeRepository(db, cache)
    service_type = service_type_repo.get_by_id_optional(str(service.service_type_id))
    if not service_type:
        return []

    # Return default scopes based on category
    return DEFAULT_SERVICE_SCOPES.get(service_type.category, [])


def create_api_token(
    token_data: ApiTokenCreate,
    permissions: Principal,
    db: Session,
    cache: Optional["Cache"] = None,
) -> ApiTokenCreateResponse:
    """
    Create a new API token.

    Args:
        token_data: Token creation data
        permissions: Current user permissions
        db: Database session
        cache: Optional cache for repository operations

    Returns:
        Created token with full token string (shown only once)

    Raises:
        BadRequestException: If user not found or token generation fails
        ForbiddenException: If user lacks permissions
    """
    # Determine target user ID
    if token_data.user_id:
        # Admin creating token for another user
        check_permissions(permissions, ApiToken, "create", db)
        target_user_id = token_data.user_id
    else:
        # User creating token for themselves
        target_user_id = permissions.user_id

    # Verify user exists
    user_repo = UserRepository(db, cache)
    user = user_repo.get_by_id_optional(str(target_user_id))
    if not user:
        raise BadRequestException(detail="User not found")

    # If not admin, verify creating token for self
    if token_data.user_id and token_data.user_id != permissions.user_id:
        check_permissions(permissions, ApiToken, "create", db)

    # Determine scopes: use provided scopes, or get defaults for service accounts
    scopes = token_data.scopes
    if not scopes:
        default_scopes = get_default_scopes_for_service(str(target_user_id), db, cache)
        if default_scopes:
            scopes = default_scopes
            logger.info(f"Using default scopes for service account {user.username}: {len(scopes)} scopes")
        else:
            scopes = []

    # Generate token with retry logic for collision handling
    for attempt in range(MAX_TOKEN_GENERATION_RETRIES):
        try:
            full_token, token_prefix, token_hash = generate_api_token()

            api_token = ApiToken(
                name=token_data.name,
                description=token_data.description,
                user_id=target_user_id,
                token_hash=token_hash,
                token_prefix=token_prefix,
                scopes=scopes,
                expires_at=token_data.expires_at,
                created_by=permissions.user_id,
            )

            db.add(api_token)
            db.flush()  # Check uniqueness constraint

            db.commit()
            db.refresh(api_token)

            logger.info(
                f"Created API token '{api_token.name}' for user {user.username} "
                f"(prefix: {token_prefix})"
            )

            return ApiTokenCreateResponse(
                id=api_token.id,
                name=api_token.name,
                description=api_token.description,
                user_id=api_token.user_id,
                token=full_token,  # Only shown once!
                token_prefix=api_token.token_prefix,
                scopes=api_token.scopes,
                expires_at=api_token.expires_at,
                created_at=api_token.created_at,
            )

        except IntegrityError:
            db.rollback()
            if attempt == MAX_TOKEN_GENERATION_RETRIES - 1:
                logger.error(
                    f"Failed to generate unique API token after {MAX_TOKEN_GENERATION_RETRIES} attempts"
                )
                raise BadRequestException(
                    detail="Failed to generate unique token - please try again"
                )
            logger.warning(f"Token collision on attempt {attempt + 1}, retrying...")
            continue

    raise BadRequestException(detail="Failed to create API token")


def get_api_token(
    token_id: UUID,
    permissions: Principal,
    db: Session,
    cache: Optional["Cache"] = None,
) -> ApiTokenGet:
    """
    Get API token details by ID.

    Users can only view their own tokens unless they have admin permissions.
    The actual token value is never returned.
    """
    token_repo = ApiTokenRepository(db, cache)
    token = token_repo.get_by_id_optional(str(token_id))
    if not token:
        raise NotFoundException(detail="API token not found")

    # Check permissions: owner or admin
    if str(token.user_id) != str(permissions.user_id):
        check_permissions(permissions, ApiToken, "read", db)

    return ApiTokenGet.model_validate(token, from_attributes=True)


def list_api_tokens(
    user_id: Optional[UUID],
    include_revoked: bool,
    permissions: Principal,
    db: Session,
    cache: Optional["Cache"] = None,
) -> List[ApiTokenGet]:
    """
    List API tokens.

    Regular users can only list their own tokens.
    Admins can list all tokens or filter by user_id.
    """
    token_repo = ApiTokenRepository(db, cache)

    # Determine which user's tokens to list
    if user_id:
        # Admin filtering by specific user
        check_permissions(permissions, ApiToken, "read", db)
        target_user_id = str(user_id)
    else:
        # Check if user can list all tokens or only their own
        try:
            check_permissions(permissions, ApiToken, "read", db)
            # Admin - can list all tokens
            target_user_id = None
        except ForbiddenException:
            # Regular user - only their own tokens
            target_user_id = str(permissions.user_id)

    # Get tokens based on filtering
    if target_user_id:
        tokens = token_repo.find_by_user(target_user_id, include_revoked=include_revoked)
    else:
        # Admin listing all tokens
        if include_revoked:
            tokens = token_repo.list()
        else:
            tokens = token_repo.find_by(revoked_at=None)

    return [ApiTokenGet.model_validate(t, from_attributes=True) for t in tokens]


def update_api_token_admin(
    token_id: UUID,
    token_data: "ApiTokenUpdate",
    permissions: Principal,
    db: Session,
    cache: Optional["Cache"] = None,
) -> ApiTokenGet:
    """
    Update an API token (admin-only).

    This endpoint is for updating token metadata, particularly scopes after
    course creation during deployment.

    Args:
        token_id: Token ID to update
        token_data: Token update data
        permissions: Current user permissions (must be admin)
        db: Database session
        cache: Optional cache for repository operations

    Returns:
        Updated token details

    Raises:
        ForbiddenException: If user is not admin
        NotFoundException: If token not found
    """
    # Require admin permissions
    check_permissions(permissions, ApiToken, "update", db)

    # Get token
    token_repo = ApiTokenRepository(db, cache)
    token = token_repo.get_by_id_optional(str(token_id))
    if not token:
        raise NotFoundException(detail="API token not found")

    try:
        # Build updates dict
        updates = {"updated_by": permissions.user_id, "updated_at": datetime.now(timezone.utc)}
        if token_data.name is not None:
            updates["name"] = token_data.name
        if token_data.description is not None:
            updates["description"] = token_data.description
        if token_data.scopes is not None:
            updates["scopes"] = token_data.scopes
        if token_data.expires_at is not None:
            updates["expires_at"] = token_data.expires_at
        if token_data.properties is not None:
            updates["properties"] = token_data.properties

        token = token_repo.update(str(token_id), updates)

        logger.info(
            f"Updated API token '{token.name}' (prefix: {token.token_prefix})"
        )

        return ApiTokenGet.model_validate(token, from_attributes=True)

    except Exception as e:
        db.rollback()
        logger.error(f"Error updating API token: {e}")
        raise


def revoke_api_token(
    token_id: UUID,
    reason: Optional[str],
    permissions: Principal,
    db: Session,
    cache: Optional["Cache"] = None,
) -> None:
    """
    Revoke an API token.

    Users can revoke their own tokens.
    Admins can revoke any token.

    Also invalidates the token's Redis cache for immediate effect.
    """
    token_repo = ApiTokenRepository(db, cache)
    token = token_repo.get_by_id_optional(str(token_id))
    if not token:
        raise NotFoundException(detail="API token not found")

    # Check if already revoked
    if token.revoked_at:
        raise BadRequestException(detail="Token is already revoked")

    # Check permissions: owner or admin
    if str(token.user_id) != str(permissions.user_id):
        check_permissions(permissions, ApiToken, "delete", db)

    try:
        revoked_token = token_repo.revoke(
            str(token_id),
            reason=reason,
            revoked_by=str(permissions.user_id)
        )

        # Invalidate token cache for immediate revocation effect
        if revoked_token:
            _invalidate_token_cache_sync(revoked_token.token_hash)

        logger.info(
            f"Revoked API token '{token.name}' (prefix: {token.token_prefix}) - "
            f"reason: {reason or 'not specified'}"
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error revoking API token: {e}")
        raise


def _invalidate_token_cache_sync(token_hash: bytes) -> None:
    """Helper to invalidate token cache from sync context."""
    import asyncio
    try:
        from computor_backend.permissions.api_token_cache import invalidate_token_cache
        token_hash_hex = token_hash.hex()

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        loop.run_until_complete(invalidate_token_cache(token_hash_hex))
    except Exception as e:
        logger.warning(f"Failed to invalidate token cache: {e}")


def create_api_token_admin(
    token_data: ApiTokenAdminCreate,
    permissions: Principal,
    db: Session,
    cache: Optional["Cache"] = None,
) -> ApiTokenCreateResponse:
    """
    Create an API token with a predefined value (admin-only).

    This endpoint is intended for initial deployment where tokens need to be
    known in advance. Regular token creation should use create_api_token().

    Args:
        token_data: Token creation data with predefined token
        permissions: Current user permissions (must be admin)
        db: Database session
        cache: Optional cache for repository operations

    Returns:
        Created token with the predefined token value

    Raises:
        ForbiddenException: If user is not admin
        BadRequestException: If user not found or token format invalid
    """
    # Require admin permissions
    check_permissions(permissions, ApiToken, "create", db)

    # Verify user exists
    user_repo = UserRepository(db, cache)
    user = user_repo.get_by_id_optional(token_data.user_id)
    if not user:
        raise BadRequestException(detail="User not found")

    # Validate token format
    predefined_token = token_data.predefined_token
    if not predefined_token.startswith("ctp_"):
        raise BadRequestException(
            detail="Predefined token must start with 'ctp_' prefix"
        )

    if len(predefined_token) < 32:
        raise BadRequestException(
            detail="Predefined token must be at least 32 characters long"
        )

    # Extract prefix (first 12 characters) and hash the token
    from computor_backend.utils.api_token import hash_api_token
    token_prefix = predefined_token[:12]
    token_hash = hash_api_token(predefined_token)

    # Determine scopes: use provided scopes, or get defaults for service accounts
    scopes = token_data.scopes
    if not scopes:
        default_scopes = get_default_scopes_for_service(token_data.user_id, db, cache)
        if default_scopes:
            scopes = default_scopes
            logger.info(f"Using default scopes for service account {user.username}: {len(scopes)} scopes")
        else:
            scopes = []

    try:
        api_token = ApiToken(
            name=token_data.name,
            description=token_data.description,
            user_id=token_data.user_id,
            token_hash=token_hash,
            token_prefix=token_prefix,
            scopes=scopes,
            expires_at=token_data.expires_at,
            created_by=permissions.user_id,
        )

        db.add(api_token)
        db.commit()
        db.refresh(api_token)

        logger.info(
            f"Created API token (admin-predefined) '{api_token.name}' for user {user.username} "
            f"(prefix: {token_prefix})"
        )

        return ApiTokenCreateResponse(
            id=api_token.id,
            name=api_token.name,
            description=api_token.description,
            user_id=api_token.user_id,
            token=predefined_token,  # Return the predefined token
            token_prefix=api_token.token_prefix,
            scopes=api_token.scopes,
            expires_at=api_token.expires_at,
            created_at=api_token.created_at,
        )

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Failed to create admin token (likely duplicate): {e}")
        raise BadRequestException(
            detail="Failed to create token - token hash may already exist"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating admin API token: {e}")
        raise


async def get_or_create_singleton_token(
    token_data: ApiTokenCreate,
    permissions: Principal,
    db: Session,
    revocation_reason: str = "replaced by new token",
    cache: Optional["Cache"] = None,
) -> ApiTokenCreateResponse:
    """
    Get or create a singleton API token by name for a user.

    Ensures exactly one active token with the given name exists per user.
    Any existing tokens with the same name are revoked before creating a new one.

    This is useful for automated systems that need a single long-lived token
    per user (e.g., workspace auto-login, CI integrations).

    Args:
        token_data: Token creation data (name is used as the singleton key)
        permissions: Current user permissions
        db: Database session
        revocation_reason: Reason recorded when revoking old tokens
        cache: Optional cache for repository operations

    Returns:
        Newly created token with full token string (shown only once)

    Note:
        Since raw tokens are not stored (only hashes), we cannot retrieve
        an existing token's value. We always mint a fresh token.
    """
    from computor_backend.permissions.api_token_cache import invalidate_token_cache

    target_user_id = token_data.user_id or str(permissions.user_id)
    token_repo = ApiTokenRepository(db, cache)

    # Find and revoke any existing tokens with this name for the user
    existing = token_repo.find_all_active_by_name(target_user_id, token_data.name)

    for old_token in existing:
        token_repo.revoke(
            str(old_token.id),
            reason=revocation_reason,
        )
        # Invalidate cache for revoked token
        try:
            await invalidate_token_cache(old_token.token_hash.hex())
        except Exception as e:
            logger.warning(f"Failed to invalidate token cache: {e}")

    if existing:
        logger.info(
            f"Revoked {len(existing)} existing '{token_data.name}' token(s) "
            f"for user {target_user_id}"
        )

    # Create the new token
    return create_api_token(token_data, permissions, db, cache)
