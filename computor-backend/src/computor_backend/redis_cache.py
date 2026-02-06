"""
Redis client and cache dependency injection.

Provides both the raw Redis client and the write-through Cache instance
for use in dependency injection throughout the application.
"""

import os
import redis
import redis.asyncio as aioredis

from computor_backend.cache import Cache

# Get Redis configuration from environment
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', '6379'))
REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', '')
REDIS_DB = int(os.environ.get('REDIS_DB', '0'))

# Initialize async Redis client for async operations
_async_redis_client = aioredis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD if REDIS_PASSWORD else None,
    db=REDIS_DB,
    decode_responses=True,  # Auto decode to strings for easier async use
    socket_connect_timeout=5,
    socket_timeout=5,
    retry_on_timeout=True,
)

# Initialize sync Redis client for Cache (which is sync)
_sync_redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD if REDIS_PASSWORD else None,
    db=REDIS_DB,
    decode_responses=False,  # We handle encoding/decoding in Cache class
    socket_connect_timeout=5,
    socket_timeout=5,
    retry_on_timeout=True,
    health_check_interval=30,
)

# Initialize write-through cache with sync client
_cache = Cache(
    client=_sync_redis_client,
    default_ttl=600  # 10 minutes default
)


async def get_redis_client() -> aioredis.Redis:
    """
    Get async Redis client for direct access.

    Use this for operations not covered by the Cache abstraction.
    This is an async function that returns an async Redis client.

    Returns:
        Async Redis client instance

    Example:
        >>> redis = await get_redis_client()
        >>> await redis.set("key", "value", ex=3600)
        >>> value = await redis.get("key")
    """
    return _async_redis_client


def get_cache() -> Cache:
    """
    Get write-through cache instance.

    This is the primary caching interface for the application.
    Use as a FastAPI dependency.

    Returns:
        Cache instance

    Example:
        >>> @router.get("/organizations/{id}")
        >>> def get_org(
        ...     id: str,
        ...     cache: Cache = Depends(get_cache),
        ...     db: Session = Depends(get_db)
        ... ):
        ...     key = cache.key("organization", id)
        ...     org = cache.get_by_key(key)
        ...     if not org:
        ...         org = db.query(Organization).filter(Organization.id == id).first()
        ...         cache.set_with_tags(key, org, tags=[f"org:{id}"])
        ...     return org
    """
    return _cache