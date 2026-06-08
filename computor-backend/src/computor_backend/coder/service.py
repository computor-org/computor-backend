"""
Business logic for Coder workspace management.

This module provides service functions for workspace operations that
require access to backend repositories and utilities.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from computor_backend.model.service import ApiToken
from computor_backend.repositories import ApiTokenRepository, UserRepository
from computor_backend.utils.api_token import generate_api_token

logger = logging.getLogger(__name__)


def mint_workspace_token(
    db: Session,
    cache,
    target_user_id: str,
    created_by: str,
    ttl_days: Optional[int] = 30,
) -> Optional[str]:
    """
    Mint an API token for workspace auto-login.

    This creates a singleton token named "workspace-auto-login" for the user.
    If a token with this name already exists, it is revoked first (rotation), so
    each provision hands the workspace a fresh token and invalidates the old one.

    The token is given a bounded lifetime (``ttl_days``) so a leaked
    COMPUTOR_AUTH_TOKEN cannot be used indefinitely; an actively-used workspace
    is re-provisioned (and thus re-minted) well within that window.

    Args:
        db: Database session
        cache: Redis cache instance
        target_user_id: User ID to create the token for
        created_by: User ID of the admin creating the token
        ttl_days: Token lifetime in days; ``None`` or <= 0 means never expire

    Returns:
        The full token string if successful, None if failed
    """
    logger.info(f"mint_workspace_token called: target={target_user_id}, by={created_by}")
    try:
        token_repo = ApiTokenRepository(db, cache)
        token_name = "workspace-auto-login"

        # Revoke existing tokens with this name (singleton pattern)
        existing = token_repo.find_all_active_by_name(target_user_id, token_name)
        for old_token in existing:
            token_repo.revoke(str(old_token.id), reason="replaced by new workspace provision")
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
        db.add(api_token)
        db.commit()

        logger.info(f"Minted workspace token for user {target_user_id} (prefix: {token_prefix}, length: {len(full_token)})")
        return full_token

    except Exception as e:
        logger.error(f"Failed to mint workspace token: {e}", exc_info=True)
        db.rollback()
        return None


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
