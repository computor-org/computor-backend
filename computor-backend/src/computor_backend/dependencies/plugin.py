"""
FastAPI dependencies for plugin integrations.

These dependencies are injected into plugin routers to provide
user information and token minting functionality.
"""

import logging
from typing import Optional

from fastapi import Depends
from sqlalchemy.orm import Session

from computor_backend.database import get_db
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.repositories.user import UserRepository
from computor_backend.redis_cache import get_cache
from computor_backend.cache import Cache
from computor_types.users import UserList

logger = logging.getLogger(__name__)

__all__ = [
    "get_current_principal",
    "get_current_user",
    "mint_workspace_token",
]


async def get_current_user(
    permissions: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache),
) -> UserList:
    """
    Get the current user as a UserList DTO (cached).

    Uses UserRepository with Redis caching for improved performance.
    Returns a UserList object containing id, email, username, given_name,
    family_name - all the fields needed by plugin routers.
    """
    repo = UserRepository(db, cache)
    user = repo.get_by_id(str(permissions.user_id))
    return UserList.model_validate(user)


async def mint_workspace_token(
    permissions: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache),
) -> Optional[str]:
    """
    Mint a singleton API token for automatic extension auth in workspaces.

    Creates a new 'workspace-auto-login' token for the user, revoking any
    existing tokens with that name. This ensures one active workspace token
    per user.
    """
    try:
        from computor_backend.business_logic.api_tokens import get_or_create_singleton_token
        from computor_types.api_tokens import ApiTokenCreate

        token_data = ApiTokenCreate(
            name="workspace-auto-login",
            description="Auto-generated token for VSCode extension in workspace",
            user_id=str(permissions.user_id),
            scopes=[],  # Empty scopes = inherits user's full permissions via role claims
        )
        result = await get_or_create_singleton_token(
            token_data,
            permissions,
            db,
            revocation_reason="replaced by new workspace provision",
            cache=cache,
        )
        logger.info(f"Minted workspace token for user {permissions.user_id} (prefix: {result.token_prefix})")
        return result.token
    except Exception as e:
        logger.warning(f"Failed to mint workspace token: {e}")
        return None
