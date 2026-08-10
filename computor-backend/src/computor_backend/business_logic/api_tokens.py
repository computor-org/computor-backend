"""Business logic for API token management."""
import logging
from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from computor_backend.exceptions import (
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
        # General workers read course data for orchestration.
        #
        # NOTE: `course:create` and `course:update` used to be granted here by
        # default, which handed every worker-category service system-wide
        # course-write authority without anyone asking for it. Since
        # assert_may_grant_scopes now also treats this table as the ceiling a
        # non-admin may grant, a broad default is doubly expensive. A worker
        # that genuinely provisions courses should have those two scopes
        # granted explicitly by an admin.
        "course:get",
        "course:list",
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


def _constraint_name(error: IntegrityError) -> str:
    """Best-effort name of the violated constraint (psycopg2 exposes diag)."""
    diag = getattr(getattr(error, "orig", None), "diag", None)
    return getattr(diag, "constraint_name", None) or ""


def _is_token_hash_collision(error: IntegrityError) -> bool:
    """True when the insert failed because the generated token hash exists.

    That is the only failure a retry can fix. Prefer the structured constraint
    name; fall back to the message for drivers that do not expose diagnostics.
    """
    name = _constraint_name(error)
    if name:
        return "token_hash" in name
    return "token_hash" in str(getattr(error, "orig", error))


def _constraint_hint(error: IntegrityError) -> str:
    """Human-readable reason for a non-collision integrity failure."""
    name = _constraint_name(error)
    if name == "ck_api_token_expiration":
        return "expires_at must be later than the token's creation time"
    return f"database constraint violated{f' ({name})' if name else ''}"


def assert_may_grant_scopes(
    target_user,
    requested_scopes: Optional[List[str]],
    permissions: Principal,
    db: Session,
    cache: Optional["Cache"] = None,
) -> None:
    """Gate WHICH scopes a caller may put on a token (the scope ceiling).

    ``assert_may_mint_token_for`` only decides *whose* token may be minted. On
    its own that left a hole: token scopes become ordinary
    ``("permissions", scope)`` claims that non-admin handlers honour, so a
    ``_service_manager`` — who holds nothing but ``service:*`` and
    ``api_token:*`` — could mint a service token carrying ``result:update`` or
    ``user:create`` and then authenticate as that service to forge grades in
    any course. Delegating machine identities is supposed to be strictly weaker
    than admin.

    The rule: an admin may grant anything; anyone else may grant only the
    scopes the target service's own type category already entitles it to
    (``DEFAULT_SERVICE_SCOPES``) — exactly the set the backend would have
    assigned by itself. That keeps the intended workflow working (provision a
    testing service, mint it its 15 testing scopes) while making it impossible
    to hand a service authority its type was never meant to have.
    """
    if permissions.is_admin or not requested_scopes:
        return

    allowed = set(get_default_scopes_for_service(str(target_user.id), db, cache))
    excess = sorted({s for s in requested_scopes if s not in allowed})
    if not excess:
        return

    raise ForbiddenException(
        detail=(
            "You may not grant these scopes: " + ", ".join(excess) + ". "
            "Only an administrator can issue a token with scopes beyond the "
            "service type's defaults."
        ),
        context={
            "target_user_id": str(target_user.id),
            "rejected_scopes": excess,
        },
    )


def assert_may_mint_token_for(user, permissions: Principal) -> None:
    """Gate minting a token on behalf of another user.

    ``check_permissions`` cannot express this rule: it returns a query over
    ``api_token``, but the constraint here is on the *target user*.

    Token scopes are additive (see ``permissions/handlers_service``), so a
    token minted on a human account carries that account's entire role set no
    matter which scopes are requested. Minting one for someone else is
    therefore an escalation, and is reserved to admins. Service accounts hold
    no roles, so a `_service_manager` minting for them grants exactly the
    scopes and nothing more.
    """
    if str(user.id) == str(permissions.user_id):
        return  # your own token — always allowed

    if permissions.is_admin:
        return

    if not user.is_service:
        raise ForbiddenException(
            detail=(
                "Only administrators can create API tokens for another user. "
                "Token scopes only add permissions, so such a token would "
                "carry that user's full authority."
            ),
            context={"target_user_id": str(user.id)},
        )

    if not permissions.permitted(ApiToken.__tablename__, "create"):
        raise ForbiddenException(
            detail="Insufficient permissions to create an API token for this service account",
            context={"target_user_id": str(user.id)},
        )


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
        ForbiddenException: If minting for another user without the authority
    """
    target_user_id = token_data.user_id or permissions.user_id

    # Verify user exists
    user_repo = UserRepository(db, cache)
    user = user_repo.get_by_id_optional(str(target_user_id))
    if not user:
        raise BadRequestException(detail="User not found")

    assert_may_mint_token_for(user, permissions)
    assert_may_grant_scopes(user, token_data.scopes, permissions, db, cache)

    # Determine scopes: use provided scopes, or get defaults for service accounts
    scopes = token_data.scopes
    if not scopes:
        default_scopes = get_default_scopes_for_service(str(target_user_id), db, cache)
        if default_scopes:
            scopes = default_scopes
            logger.info(f"Using default scopes for service account {user.email}: {len(scopes)} scopes")
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
                f"Created API token '{api_token.name}' for user {user.email} "
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

        except IntegrityError as e:
            db.rollback()

            # Retrying only makes sense for a token-hash collision — a fresh
            # random value fixes that. Any other constraint (e.g. the
            # expires_at > created_at CHECK) fails identically on all five
            # attempts and then reported "Failed to generate unique token",
            # which pointed at the wrong thing entirely.
            if not _is_token_hash_collision(e):
                logger.error(f"API token insert violated a constraint: {e}")
                raise BadRequestException(
                    detail=f"Could not create API token: {_constraint_hint(e)}"
                ) from e

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

    Users can only view their own tokens; a `_service_manager` additionally
    sees tokens owned by service accounts; admins see everything. The actual
    token value is never returned.

    The row MUST be fetched through the query ``check_permissions`` returns.
    ``ApiTokenPermissionHandler`` narrows rather than raises (everyone owns
    some tokens), so a bare repository lookup after a successful
    ``check_permissions`` would read any user's token.
    """
    query = check_permissions(permissions, ApiToken, "get", db)

    # str(): the UUID column type rejects uuid.UUID objects in a filter
    # (StatementError). The endpoint declares token_id as UUID, so this cast
    # is required at every one of these call sites.
    token = query.filter(ApiToken.id == str(token_id)).first()
    if not token:
        raise NotFoundException(detail="API token not found")

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

    Visibility comes entirely from ``ApiTokenPermissionHandler``: a regular
    user sees their own, a `_service_manager` sees service-owned tokens plus
    their own, an admin sees everything. ``user_id`` narrows within that set —
    asking for a user you cannot see yields an empty list, not a 403.
    """
    query = check_permissions(permissions, ApiToken, "list", db)

    if user_id:
        query = query.filter(ApiToken.user_id == str(user_id))

    if not include_revoked:
        query = query.filter(ApiToken.revoked_at.is_(None))

    return [
        ApiTokenGet.model_validate(t, from_attributes=True) for t in query.all()
    ]


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
        ForbiddenException: If the caller may not act on this token
        NotFoundException: If token not found
    """
    token_repo = ApiTokenRepository(db, cache)

    # Fetch through the permitted query: rewriting a token's scopes is the
    # most direct escalation there is, so it must be scoped exactly like a
    # read. ApiTokenPermissionHandler narrows instead of raising, so a bare
    # get_by_id_optional here would let any caller re-scope any token.
    query = check_permissions(permissions, ApiToken, "update", db)
    token = query.filter(ApiToken.id == str(token_id)).first()
    if not token:
        raise NotFoundException(detail="API token not found")

    # Re-scoping is minting by another name — apply the same ceiling, or a
    # non-admin could simply PATCH the scopes they were refused at create time.
    if token_data.scopes is not None:
        token_owner = UserRepository(db, cache).get_by_id_optional(str(token.user_id))
        if token_owner is None:
            raise NotFoundException(detail="API token owner not found")
        assert_may_grant_scopes(token_owner, token_data.scopes, permissions, db, cache)

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

    Users can revoke their own tokens; a `_service_manager` can also revoke a
    service account's; admins can revoke any.

    Fetched through the permitted query, not by id — revoking someone else's
    token is a denial of service, so the same narrowing that applies to reads
    must apply here. See ``get_api_token`` for why a bare lookup is unsafe.

    Also invalidates the token's Redis cache for immediate effect.
    """
    token_repo = ApiTokenRepository(db, cache)

    query = check_permissions(permissions, ApiToken, "delete", db)
    token = query.filter(ApiToken.id == str(token_id)).first()
    if not token:
        raise NotFoundException(detail="API token not found")

    # Check if already revoked
    if token.revoked_at:
        raise BadRequestException(detail="Token is already revoked")

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
    """Helper to clear a revoked token's caches from sync context.

    Uses ``revoke_token_caches`` so the principal kill-switch is raised too -
    dropping only the token cache would leave the token working for up to
    AUTH_CACHE_TTL via the cached Principal.
    """
    import asyncio
    try:
        from computor_backend.permissions.api_token_cache import revoke_token_caches
        token_hash_hex = token_hash.hex()

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        loop.run_until_complete(revoke_token_caches(token_hash_hex))
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
        ForbiddenException: If minting for another user without the authority
        BadRequestException: If user not found or token format invalid
    """
    # Verify user exists
    user_repo = UserRepository(db, cache)
    user = user_repo.get_by_id_optional(token_data.user_id)
    if not user:
        raise BadRequestException(detail="User not found")

    # Same rule as create_api_token: a predefined value doesn't make minting
    # for a human account any less of an escalation.
    assert_may_mint_token_for(user, permissions)
    assert_may_grant_scopes(user, token_data.scopes, permissions, db, cache)

    # Validate the token with the SAME validator authentication uses.
    #
    # This used to accept anything starting with "ctp_" and at least 32 chars
    # long, but permissions/auth.py rejects a token that is not exactly
    # len("ctp_") + 32 characters of url-safe base64 *before* it ever hashes
    # it. A 40-character or oddly-charactered value was therefore stored
    # happily and then failed every single authentication with "Invalid API
    # token format" — a token dead on arrival, with nothing flagged at
    # creation time. Reject it here instead.
    from computor_backend.utils.api_token import validate_token_format

    predefined_token = token_data.predefined_token
    if not validate_token_format(predefined_token):
        raise BadRequestException(
            detail=(
                "Predefined token is not a valid Computor API token. It must be "
                "'ctp_' followed by exactly 32 url-safe base64 characters "
                "(A-Z a-z 0-9 - _), e.g. the output of "
                "`computor token create`. A token that does not match this "
                "format would be stored but rejected at every authentication."
            )
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
            logger.info(f"Using default scopes for service account {user.email}: {len(scopes)} scopes")
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
            f"Created API token (admin-predefined) '{api_token.name}' for user {user.email} "
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
        ) from e
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
    from computor_backend.permissions.api_token_cache import revoke_token_caches

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
            await revoke_token_caches(old_token.token_hash.hex())
        except Exception as e:
            logger.warning(f"Failed to invalidate token cache: {e}")

    if existing:
        logger.info(
            f"Revoked {len(existing)} existing '{token_data.name}' token(s) "
            f"for user {target_user_id}"
        )

    # Create the new token
    return create_api_token(token_data, permissions, db, cache)
