"""
Business logic for Coder workspace management.

This module provides service functions for workspace operations that
require access to backend repositories and utilities.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from computor_backend.model.service import ApiToken
from computor_backend.permissions.api_token_cache import invalidate_token_cache_sync
from computor_backend.repositories import ApiTokenRepository, DuplicateError, UserRepository
from computor_backend.utils.api_token import generate_api_token

logger = logging.getLogger(__name__)


@dataclass
class MintResult:
    """Outcome of a workspace token rotation.

    Carries what the caller needs to deliver the token to the workspace
    (``token``) and to undo the rotation if that delivery fails
    (``new_token_id`` / ``superseded_ids`` — see
    rollback_workspace_token_rotation).
    """

    token: str
    new_token_id: str
    superseded_ids: List[str] = field(default_factory=list)


def mint_workspace_token(
    db: Session,
    cache,
    target_user_id: str,
    created_by: str,
    workspace_name: str,
    ttl_days: Optional[int] = 30,
) -> Optional[MintResult]:
    """
    Mint an API token for workspace auto-login.

    This creates a per-workspace singleton token named
    "workspace-auto-login:{workspace_name}". If a token with this name already
    exists, it is revoked first (rotation), so each provision hands THAT
    workspace a fresh token and invalidates its old one — tokens of the user's
    other workspaces stay valid.

    The token is given a bounded lifetime (``ttl_days``) so a leaked
    COMPUTOR_AUTH_TOKEN cannot be used indefinitely; an actively-used workspace
    is re-provisioned (and thus re-minted) well within that window.

    Args:
        db: Database session
        cache: Redis cache instance
        target_user_id: User ID to create the token for
        created_by: User ID of the admin creating the token
        workspace_name: Effective (sanitized) workspace name the token is for
        ttl_days: Token lifetime in days; ``None`` or <= 0 means never expire

    Returns:
        A MintResult if successful, None if failed. Callers must treat None
        as fatal for provisioning — a workspace without a token cannot
        authenticate its VSCode extension.
    """
    logger.info(
        f"mint_workspace_token called: target={target_user_id}, by={created_by}, "
        f"workspace={workspace_name}"
    )
    try:
        return _rotate_workspace_token(
            db, cache, target_user_id, created_by, workspace_name, ttl_days
        )
    except DuplicateError:
        # Lost a race with a concurrent provision of this workspace: its token
        # hit the active-token unique index first. Re-read past the cache and
        # rotate whatever is active now — exactly one retry.
        db.rollback()
        try:
            return _rotate_workspace_token(
                db, cache, target_user_id, created_by, workspace_name, ttl_days,
                fresh_read=True,
            )
        except Exception as e:
            logger.error(
                f"Failed to mint workspace token after conflict retry: {e}",
                exc_info=True,
            )
            db.rollback()
            return None
    except Exception as e:
        logger.error(f"Failed to mint workspace token: {e}", exc_info=True)
        db.rollback()
        return None


def _rotate_workspace_token(
    db: Session,
    cache,
    target_user_id: str,
    created_by: str,
    workspace_name: str,
    ttl_days: Optional[int],
    fresh_read: bool = False,
) -> MintResult:
    """One revoke-predecessors-then-create pass; raises on any failure."""
    token_repo = ApiTokenRepository(db, cache)
    token_name = f"workspace-auto-login:{workspace_name}"

    lookup_names = [token_name]
    # Tokens minted before the per-workspace scheme were named plain
    # "workspace-auto-login" and belonged to the old default workspace
    # ("workspace") — rotate those too when re-provisioning it.
    if workspace_name == "workspace":
        lookup_names.append("workspace-auto-login")

    if fresh_read and cache is not None:
        # On conflict retry the cached active-token list may predate the
        # competing mint's commit — evict it so the re-read sees that token.
        cache.invalidate_tags(
            *(f"api_token:name:{target_user_id}:{name}" for name in lookup_names)
        )

    # Revoke existing tokens with these names (per-workspace singleton)
    existing = []
    for name in lookup_names:
        existing.extend(token_repo.find_all_active_by_name(target_user_id, name))

    superseded_ids: List[str] = []
    superseded_hashes: List[str] = []
    for old_token in existing:
        revoked = token_repo.revoke(
            str(old_token.id),
            reason="replaced by new workspace provision",
            revoked_by=created_by,
        )
        if revoked is not None:
            superseded_ids.append(str(revoked.id))
            if revoked.token_hash:
                superseded_hashes.append(revoked.token_hash.hex())
        logger.info(f"Revoked existing workspace token: {old_token.id}")

    # Generate and create new token
    full_token, token_prefix, token_hash = generate_api_token()
    expires_at = None
    if ttl_days and ttl_days > 0:
        expires_at = datetime.now(timezone.utc) + timedelta(days=ttl_days)
    api_token = ApiToken(
        name=token_name,
        description="Auto-generated token for VSCode extension in workspace",
        user_id=target_user_id,
        token_hash=token_hash,
        token_prefix=token_prefix,
        scopes=[],
        expires_at=expires_at,
        created_by=created_by,
    )
    try:
        # create() (not raw db.add): its deferred tag invalidation fires on
        # commit, so a later find_all_active_by_name cannot serve a stale list
        # that misses this token and skips its revocation.
        token_repo.create(api_token)
        db.commit()
    except Exception:
        # The revocations above already committed; restore them so the running
        # workspace keeps its still-deployed old token when minting fails.
        # (Best-effort — after a lost race the restore is correctly rejected
        # by the active-token unique index, since the winner's token is live.)
        for old_id in superseded_ids:
            try:
                token_repo.unrevoke(old_id, unrevoked_by=created_by)
            except Exception:
                logger.warning(
                    f"Could not restore superseded workspace token {old_id}",
                    exc_info=True,
                )
        raise

    # The rotated-out tokens may survive in the auth cache for its TTL —
    # drop them so revocation takes effect immediately.
    for hash_hex in superseded_hashes:
        invalidate_token_cache_sync(hash_hex)

    logger.info(f"Minted workspace token for user {target_user_id} (prefix: {token_prefix}, length: {len(full_token)})")
    return MintResult(
        token=full_token,
        new_token_id=str(api_token.id),
        superseded_ids=superseded_ids,
    )


def rollback_workspace_token_rotation(
    db: Session,
    cache,
    mint_result: MintResult,
    revoked_by: str,
) -> None:
    """
    Compensate a token rotation whose workspace provisioning failed.

    The freshly minted token never reached the workspace — revoke it — and the
    superseded token's plaintext is still deployed inside the running
    workspace, so restore it to keep that workspace's extension working. The
    new token must be revoked BEFORE the old one is restored, or the
    active-token unique index rejects the restore.

    Best-effort: never raises, so callers can re-raise the provisioning error.
    """
    token_repo = ApiTokenRepository(db, cache)
    try:
        revoked = token_repo.revoke(
            mint_result.new_token_id,
            reason="workspace provisioning failed",
            revoked_by=revoked_by,
        )
        if revoked is not None and revoked.token_hash:
            invalidate_token_cache_sync(revoked.token_hash.hex())
    except Exception:
        db.rollback()
        logger.warning(
            f"Could not revoke undelivered workspace token "
            f"{mint_result.new_token_id}; skipping restore of its predecessors",
            exc_info=True,
        )
        return

    for old_id in mint_result.superseded_ids:
        try:
            token_repo.unrevoke(old_id, unrevoked_by=revoked_by)
        except Exception:
            logger.warning(
                f"Could not restore superseded workspace token {old_id}",
                exc_info=True,
            )


def get_user_by_id(db: Session, cache, user_id: str):
    """
    Get a user by ID from the database.

    Args:
        db: Database session
        cache: Redis cache instance
        user_id: User ID to look up

    Returns:
        User object if found

    Raises:
        NotFoundError: If user not found
    """
    user_repo = UserRepository(db, cache)
    return user_repo.get_by_id(user_id)


def get_user_by_email(db: Session, cache, email: str):
    """
    Get a user by email from the database.

    Args:
        db: Database session
        cache: Redis cache instance
        email: Email address to look up

    Returns:
        User object if found, None if not found
    """
    user_repo = UserRepository(db, cache)
    return user_repo.find_by_email(email)


def get_user_email(user) -> str:
    """
    Get user email with fallback to username@computor.local.

    Args:
        user: User object with email and username attributes

    Returns:
        Email string
    """
    return user.email or f"user_{user.id}@computor.local"


def get_user_fullname(user) -> Optional[str]:
    """
    Get user full name if both given and family name are set.

    Args:
        user: User object with given_name and family_name attributes

    Returns:
        Full name string or None
    """
    if user.given_name and user.family_name:
        return f"{user.given_name} {user.family_name}"
    return None
