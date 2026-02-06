"""
Business logic for Coder workspace management.

This module provides service functions for workspace operations that
require access to backend repositories and utilities.
"""

import logging
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
) -> Optional[str]:
    """
    Mint an API token for workspace auto-login.

    This creates a singleton token named "workspace-auto-login" for the user.
    If a token with this name already exists, it is revoked first.

    Args:
        db: Database session
        cache: Redis cache instance
        target_user_id: User ID to create the token for
        created_by: User ID of the admin creating the token

    Returns:
        The full token string if successful, None if failed
    """
    print(f"[TOKEN] mint_workspace_token called: target={target_user_id}, by={created_by}")
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
        api_token = ApiToken(
            name=token_name,
            description="Auto-generated token for VSCode extension in workspace",
            user_id=target_user_id,
            token_hash=token_hash,
            token_prefix=token_prefix,
            scopes=[],
            created_by=created_by,
        )
        db.add(api_token)
        db.commit()

        print(f"[TOKEN] SUCCESS: minted token prefix={token_prefix}, length={len(full_token)}")
        logger.info(f"Minted workspace token for user {target_user_id} (prefix: {token_prefix}, length: {len(full_token)})")
        return full_token

    except Exception as e:
        print(f"[TOKEN] FAILED: {e}")
        import traceback
        traceback.print_exc()
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
    return user.email if user.email else f"{user.username}@computor.local"


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
