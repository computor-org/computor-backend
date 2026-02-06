"""
API Token caching layer for improved authentication performance.

Provides Redis-based caching for API token validation to avoid database
queries on every request.

Cache Strategy:
- Token validation results cached for 120 seconds
- Revocation invalidates cache immediately
- Rate limiting for token minting
"""

import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Configuration
API_TOKEN_CACHE_TTL = 120  # 2 minutes - balance between performance and revocation latency


class CachedTokenData:
    """Cached API token authentication data."""

    def __init__(
        self,
        token_id: str,
        user_id: str,
        role_ids: List[str],
        scopes: List[str],
        expires_at: Optional[str],  # ISO format string
        token_prefix: str,
    ):
        self.token_id = token_id
        self.user_id = user_id
        self.role_ids = role_ids
        self.scopes = scopes
        self.expires_at = expires_at
        self.token_prefix = token_prefix

    def to_dict(self) -> Dict[str, Any]:
        return {
            "token_id": self.token_id,
            "user_id": self.user_id,
            "role_ids": self.role_ids,
            "scopes": self.scopes,
            "expires_at": self.expires_at,
            "token_prefix": self.token_prefix,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CachedTokenData":
        return cls(
            token_id=data["token_id"],
            user_id=data["user_id"],
            role_ids=data["role_ids"],
            scopes=data.get("scopes", []),
            expires_at=data.get("expires_at"),
            token_prefix=data["token_prefix"],
        )

    def is_expired(self) -> bool:
        """Check if token has expired based on cached expiration time."""
        if not self.expires_at:
            return False
        try:
            exp = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
            return exp < datetime.now(timezone.utc)
        except (ValueError, AttributeError):
            return False


async def get_cached_token_data(
    token_hash_hex: str,
) -> Optional[CachedTokenData]:
    """
    Get cached API token data from Redis.

    Args:
        token_hash_hex: Hex string of the token hash

    Returns:
        CachedTokenData if found and valid, None otherwise
    """
    from computor_backend.redis_cache import get_redis_client

    cache_key = f"api_token:auth:{token_hash_hex}"

    try:
        redis_client = await get_redis_client()
        cached_raw = await redis_client.get(cache_key)

        if cached_raw:
            data = json.loads(cached_raw)
            token_data = CachedTokenData.from_dict(data)

            # Check expiration even from cache
            if token_data.is_expired():
                logger.debug(f"Cached token {token_data.token_prefix}... has expired")
                await redis_client.delete(cache_key)
                return None

            logger.debug(f"Cache HIT for API token {token_data.token_prefix}...")
            return token_data
    except Exception as e:
        logger.warning(f"Redis cache read error for API token: {e}")

    return None


async def set_cached_token_data(
    token_hash_hex: str,
    token_data: CachedTokenData,
    ttl: int = API_TOKEN_CACHE_TTL,
) -> None:
    """
    Cache API token data in Redis.

    Args:
        token_hash_hex: Hex string of the token hash
        token_data: Token data to cache
        ttl: Time-to-live in seconds
    """
    from computor_backend.redis_cache import get_redis_client

    cache_key = f"api_token:auth:{token_hash_hex}"

    try:
        redis_client = await get_redis_client()
        await redis_client.set(
            cache_key,
            json.dumps(token_data.to_dict()),
            ex=ttl,
        )
        logger.debug(f"Cached API token {token_data.token_prefix}... (TTL: {ttl}s)")
    except Exception as e:
        logger.warning(f"Redis cache write error for API token: {e}")


async def invalidate_token_cache(token_hash_hex: str) -> None:
    """
    Invalidate cached token data (call on revocation).

    Args:
        token_hash_hex: Hex string of the token hash
    """
    from computor_backend.redis_cache import get_redis_client

    cache_key = f"api_token:auth:{token_hash_hex}"

    try:
        redis_client = await get_redis_client()
        await redis_client.delete(cache_key)
        logger.info(f"Invalidated API token cache: {token_hash_hex[:16]}...")
    except Exception as e:
        logger.warning(f"Failed to invalidate API token cache: {e}")


async def invalidate_user_token_caches(user_id: str) -> None:
    """
    Invalidate all cached tokens for a user.

    This is a best-effort operation - it clears what it can find.
    Tokens will naturally expire from cache after TTL.

    Args:
        user_id: User whose tokens should be invalidated
    """
    from computor_backend.redis_cache import get_redis_client

    # We track user -> token mappings for efficient invalidation
    user_tokens_key = f"api_token:user:{user_id}:tokens"

    try:
        redis_client = await get_redis_client()
        token_hashes = await redis_client.smembers(user_tokens_key)

        if token_hashes:
            # Delete all cached token data
            cache_keys = [f"api_token:auth:{h}" for h in token_hashes]
            await redis_client.delete(*cache_keys)
            await redis_client.delete(user_tokens_key)
            logger.info(f"Invalidated {len(token_hashes)} cached tokens for user {user_id}")
    except Exception as e:
        logger.warning(f"Failed to invalidate user token caches: {e}")


async def track_user_token(user_id: str, token_hash_hex: str) -> None:
    """
    Track which tokens belong to a user for bulk invalidation.

    Args:
        user_id: User ID
        token_hash_hex: Token hash to track
    """
    from computor_backend.redis_cache import get_redis_client

    user_tokens_key = f"api_token:user:{user_id}:tokens"

    try:
        redis_client = await get_redis_client()
        await redis_client.sadd(user_tokens_key, token_hash_hex)
        # Set TTL slightly longer than token cache TTL
        await redis_client.expire(user_tokens_key, API_TOKEN_CACHE_TTL * 2)
    except Exception as e:
        logger.debug(f"Failed to track user token: {e}")


# =============================================================================
# Rate Limiting for Token Minting
# =============================================================================

async def check_token_mint_rate_limit(user_id: str, limit: int = 5, window: int = 60) -> bool:
    """
    Check if user is within rate limit for token minting.

    Args:
        user_id: User attempting to mint token
        limit: Maximum tokens per window
        window: Time window in seconds

    Returns:
        True if within limit, False if rate limited
    """
    from computor_backend.redis_cache import get_redis_client

    rate_key = f"rate:token_mint:{user_id}"

    try:
        redis_client = await get_redis_client()

        # Get current count
        current = await redis_client.get(rate_key)
        current_count = int(current) if current else 0

        if current_count >= limit:
            logger.warning(f"Rate limit exceeded for token minting: user {user_id}")
            return False

        # Increment counter
        pipe = redis_client.pipeline()
        pipe.incr(rate_key)
        pipe.expire(rate_key, window)
        await pipe.execute()

        return True
    except Exception as e:
        logger.warning(f"Rate limit check failed: {e}")
        # Fail open - allow the request if Redis is down
        return True


async def record_token_mint(user_id: str) -> None:
    """
    Record a token mint event for rate limiting.

    Args:
        user_id: User who minted token
    """
    # This is handled by check_token_mint_rate_limit which increments on success
    pass
