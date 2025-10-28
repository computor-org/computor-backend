"""Business logic for API token management."""
import logging
from datetime import datetime, timezone
from typing import List, Optional
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
from computor_backend.model.auth import User
from computor_backend.utils.api_token import generate_api_token
from computor_types.api_tokens import (
    ApiTokenCreate,
    ApiTokenCreateResponse,
    ApiTokenGet,
)

logger = logging.getLogger(__name__)

# Maximum retry attempts for token generation (collision handling)
MAX_TOKEN_GENERATION_RETRIES = 5


def create_api_token(
    token_data: ApiTokenCreate,
    permissions: Principal,
    db: Session,
) -> ApiTokenCreateResponse:
    """
    Create a new API token.

    Args:
        token_data: Token creation data
        permissions: Current user permissions
        db: Database session

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
    user = db.query(User).filter(User.id == target_user_id).first()
    if not user:
        raise BadRequestException(detail="User not found")

    # If not admin, verify creating token for self
    if token_data.user_id and token_data.user_id != permissions.user_id:
        check_permissions(permissions, ApiToken, "create", db)

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
                scopes=token_data.scopes or [],
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
) -> ApiTokenGet:
    """
    Get API token details by ID.

    Users can only view their own tokens unless they have admin permissions.
    The actual token value is never returned.
    """
    token = db.query(ApiToken).filter(ApiToken.id == token_id).first()
    if not token:
        raise NotFoundException(detail="API token not found")

    # Check permissions: owner or admin
    if token.user_id != permissions.user_id:
        check_permissions(permissions, ApiToken, "read", db)

    return ApiTokenGet.model_validate(token, from_attributes=True)


def list_api_tokens(
    user_id: Optional[UUID],
    include_revoked: bool,
    permissions: Principal,
    db: Session,
) -> List[ApiTokenGet]:
    """
    List API tokens.

    Regular users can only list their own tokens.
    Admins can list all tokens or filter by user_id.
    """
    # Start with base query
    query = db.query(ApiToken)

    # Determine filtering
    if user_id:
        # Admin filtering by specific user
        check_permissions(permissions, ApiToken, "read", db)
        query = query.filter(ApiToken.user_id == user_id)
    else:
        # Check if user can list all tokens or only their own
        try:
            check_permissions(permissions, ApiToken, "read", db)
            # Admin - can list all tokens (no filter)
        except ForbiddenException:
            # Regular user - only their own tokens
            query = query.filter(ApiToken.user_id == permissions.user_id)

    # Filter revoked tokens
    if not include_revoked:
        query = query.filter(ApiToken.revoked_at.is_(None))

    tokens = query.all()

    return [ApiTokenGet.model_validate(t, from_attributes=True) for t in tokens]


def revoke_api_token(
    token_id: UUID,
    reason: Optional[str],
    permissions: Principal,
    db: Session,
) -> None:
    """
    Revoke an API token.

    Users can revoke their own tokens.
    Admins can revoke any token.
    """
    token = db.query(ApiToken).filter(ApiToken.id == token_id).first()
    if not token:
        raise NotFoundException(detail="API token not found")

    # Check if already revoked
    if token.revoked_at:
        raise BadRequestException(detail="Token is already revoked")

    # Check permissions: owner or admin
    if token.user_id != permissions.user_id:
        check_permissions(permissions, ApiToken, "delete", db)

    try:
        token.revoked_at = datetime.now(timezone.utc)
        token.revocation_reason = reason
        token.updated_by = permissions.user_id

        db.commit()

        logger.info(
            f"Revoked API token '{token.name}' (prefix: {token.token_prefix}) - "
            f"reason: {reason or 'not specified'}"
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error revoking API token: {e}")
        raise
