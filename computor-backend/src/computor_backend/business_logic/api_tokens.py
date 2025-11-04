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
from computor_backend.model.service import ApiToken, Service, ServiceType
from computor_backend.model.auth import User
from computor_backend.utils.api_token import generate_api_token
from computor_types.api_tokens import (
    ApiTokenCreate,
    ApiTokenAdminCreate,
    ApiTokenCreateResponse,
    ApiTokenGet,
    ApiTokenUpdate,
)

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


def get_default_scopes_for_service(user_id: str, db: Session) -> List[str]:
    """
    Get default scopes for a service account based on its service type.

    Args:
        user_id: Service user ID
        db: Database session

    Returns:
        List of default scope strings, or empty list if not a service or no defaults
    """
    # Check if user is a service account
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_service:
        return []

    # Get the service record
    service = db.query(Service).filter(
        Service.user_id == user_id,
        Service.archived_at.is_(None)
    ).first()
    if not service or not service.service_type_id:
        return []

    # Get the service type to determine category
    service_type = db.query(ServiceType).filter(ServiceType.id == service.service_type_id).first()
    if not service_type:
        return []

    # Return default scopes based on category
    return DEFAULT_SERVICE_SCOPES.get(service_type.category, [])


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

    # Determine scopes: use provided scopes, or get defaults for service accounts
    scopes = token_data.scopes
    if not scopes:
        default_scopes = get_default_scopes_for_service(target_user_id, db)
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
) -> ApiTokenGet:
    """
    Get API token details by ID.

    Users can only view their own tokens unless they have admin permissions.
    The actual token value is never returned.
    """
    token = db.query(ApiToken).filter(ApiToken.id == str(token_id)).first()
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
        query = query.filter(ApiToken.user_id == str(user_id))
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


def update_api_token_admin(
    token_id: UUID,
    token_data: "ApiTokenUpdate",
    permissions: Principal,
    db: Session,
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

    Returns:
        Updated token details

    Raises:
        ForbiddenException: If user is not admin
        NotFoundException: If token not found
    """
    # Require admin permissions
    check_permissions(permissions, ApiToken, "update", db)

    # Get token
    token = db.query(ApiToken).filter(ApiToken.id == str(token_id)).first()
    if not token:
        raise NotFoundException(detail="API token not found")

    try:
        # Update fields if provided
        if token_data.name is not None:
            token.name = token_data.name
        if token_data.description is not None:
            token.description = token_data.description
        if token_data.scopes is not None:
            token.scopes = token_data.scopes
        if token_data.expires_at is not None:
            token.expires_at = token_data.expires_at
        if token_data.properties is not None:
            token.properties = token_data.properties

        token.updated_by = permissions.user_id
        token.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(token)

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
) -> None:
    """
    Revoke an API token.

    Users can revoke their own tokens.
    Admins can revoke any token.
    """
    token = db.query(ApiToken).filter(ApiToken.id == str(token_id)).first()
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


def create_api_token_admin(
    token_data: ApiTokenAdminCreate,
    permissions: Principal,
    db: Session,
) -> ApiTokenCreateResponse:
    """
    Create an API token with a predefined value (admin-only).

    This endpoint is intended for initial deployment where tokens need to be
    known in advance. Regular token creation should use create_api_token().

    Args:
        token_data: Token creation data with predefined token
        permissions: Current user permissions (must be admin)
        db: Database session

    Returns:
        Created token with the predefined token value

    Raises:
        ForbiddenException: If user is not admin
        BadRequestException: If user not found or token format invalid
    """
    # Require admin permissions
    check_permissions(permissions, ApiToken, "create", db)

    # Verify user exists
    user = db.query(User).filter(User.id == token_data.user_id).first()
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
        default_scopes = get_default_scopes_for_service(token_data.user_id, db)
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
