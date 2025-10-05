"""
Cache decorators for business logic functions.

Provides decorators to transparently add caching to business logic functions
without modifying their core implementation.
"""

import functools
import logging
from typing import Callable, Any, List, Optional, Set

from .cache import Cache

logger = logging.getLogger(__name__)


def cached(
    key_func: Callable[..., str],
    tags_func: Callable[..., Set[str]],
    ttl: Optional[int] = None,
    cache_param: str = "cache"
):
    """
    Decorator for caching business logic function results.

    The decorated function must accept a `cache` parameter (or custom name via cache_param).
    If cache is None, the function runs without caching.

    Args:
        key_func: Function that generates cache key from function arguments
                  Signature: (*args, **kwargs) -> str
        tags_func: Function that generates cache tags from function arguments
                   Signature: (*args, **kwargs) -> Set[str]
        ttl: Time-to-live in seconds (uses cache default if None)
        cache_param: Name of the cache parameter in the decorated function (default: "cache")

    Returns:
        Decorated function

    Example:
        >>> @cached(
        ...     key_func=lambda artifact_id, **kw: f"computor:artifact:{artifact_id}",
        ...     tags_func=lambda artifact_id, **kw: {f"artifact:{artifact_id}"},
        ...     ttl=300
        ... )
        ... def get_submission_artifact(
        ...     artifact_id: str,
        ...     permissions: Principal,
        ...     db: Session,
        ...     cache: Cache = None,
        ... ) -> SubmissionArtifact:
        ...     # ... implementation ...
        ...     pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache: Optional[Cache] = kwargs.get(cache_param)

            # If no cache provided, run function normally
            if cache is None:
                return func(*args, **kwargs)

            # Build cache key
            try:
                key = key_func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Error building cache key for {func.__name__}: {e}")
                return func(*args, **kwargs)

            # Try cache
            cached = cache.get_by_key(key)
            if cached is not None:
                logger.debug(f"Cache HIT for {func.__name__}: {key}")
                return cached

            # Cache miss - execute function
            logger.debug(f"Cache MISS for {func.__name__}: {key}")
            result = func(*args, **kwargs)

            # Store in cache with tags
            try:
                tags = tags_func(*args, **kwargs)
                cache.set_with_tags(key, result, tags, ttl)
            except Exception as e:
                logger.error(f"Error caching result for {func.__name__}: {e}")

            return result

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache: Optional[Cache] = kwargs.get(cache_param)

            # If no cache provided, run function normally
            if cache is None:
                return await func(*args, **kwargs)

            # Build cache key
            try:
                key = key_func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Error building cache key for {func.__name__}: {e}")
                return await func(*args, **kwargs)

            # Try cache
            cached = cache.get_by_key(key)
            if cached is not None:
                logger.debug(f"Cache HIT for {func.__name__}: {key}")
                return cached

            # Cache miss - execute function
            logger.debug(f"Cache MISS for {func.__name__}: {key}")
            result = await func(*args, **kwargs)

            # Store in cache with tags
            try:
                tags = tags_func(*args, **kwargs)
                cache.set_with_tags(key, result, tags, ttl)
            except Exception as e:
                logger.error(f"Error caching result for {func.__name__}: {e}")

            return result

        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def invalidate_on_write(
    tags_func: Callable[..., Set[str]],
    cache_param: str = "cache"
):
    """
    Decorator to invalidate cache tags after a write operation.

    Use this on create/update/delete functions to ensure cache stays consistent.

    Args:
        tags_func: Function that generates cache tags to invalidate
                   Signature: (*args, **kwargs) -> Set[str]
        cache_param: Name of the cache parameter (default: "cache")

    Returns:
        Decorated function

    Example:
        >>> @invalidate_on_write(
        ...     tags_func=lambda org_id, **kw: {f"org:{org_id}", "org:list"}
        ... )
        ... def update_organization(
        ...     org_id: str,
        ...     updates: dict,
        ...     db: Session,
        ...     cache: Cache = None,
        ... ) -> Organization:
        ...     # ... update logic ...
        ...     return updated_org
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Execute function
            result = func(*args, **kwargs)

            # Invalidate cache tags
            cache: Optional[Cache] = kwargs.get(cache_param)
            if cache:
                try:
                    tags = tags_func(*args, **kwargs)
                    cache.invalidate_tags(*tags)
                    logger.debug(f"Invalidated tags for {func.__name__}: {tags}")
                except Exception as e:
                    logger.error(f"Error invalidating cache for {func.__name__}: {e}")

            return result

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Execute function
            result = await func(*args, **kwargs)

            # Invalidate cache tags
            cache: Optional[Cache] = kwargs.get(cache_param)
            if cache:
                try:
                    tags = tags_func(*args, **kwargs)
                    cache.invalidate_tags(*tags)
                    logger.debug(f"Invalidated tags for {func.__name__}: {tags}")
                except Exception as e:
                    logger.error(f"Error invalidating cache for {func.__name__}: {e}")

            return result

        # Return appropriate wrapper
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def cache_list(
    key_func: Callable[..., str],
    tags_func: Callable[..., Set[str]],
    ttl: Optional[int] = None,
    cache_param: str = "cache"
):
    """
    Decorator for caching list/query results.

    Similar to @cached but designed for functions that return lists.
    Serializes/deserializes list results properly.

    Args:
        key_func: Function to generate cache key
        tags_func: Function to generate cache tags
        ttl: Time-to-live in seconds
        cache_param: Name of the cache parameter

    Returns:
        Decorated function

    Example:
        >>> @cache_list(
        ...     key_func=lambda course_id, **kw: f"computor:course_members:{course_id}",
        ...     tags_func=lambda course_id, **kw: {f"course:{course_id}", "course_member:list"},
        ...     ttl=900
        ... )
        ... def get_course_members(
        ...     course_id: str,
        ...     db: Session,
        ...     cache: Cache = None,
        ... ) -> List[CourseMember]:
        ...     # ... implementation ...
        ...     pass
    """
    return cached(key_func=key_func, tags_func=tags_func, ttl=ttl, cache_param=cache_param)


class CacheContext:
    """
    Context manager for batch cache operations.

    Useful for warming cache or performing multiple operations atomically.

    Example:
        >>> with CacheContext(cache) as ctx:
        ...     ctx.set("key1", data1, tags=["tag1"])
        ...     ctx.set("key2", data2, tags=["tag1", "tag2"])
        ...     # All operations committed at once
    """

    def __init__(self, cache: Cache):
        """
        Initialize cache context.

        Args:
            cache: Cache instance
        """
        self.cache = cache
        self._operations: List[Callable] = []

    def __enter__(self):
        """Enter context."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit context and execute all operations.

        If an exception occurred, operations are not executed.
        """
        if exc_type is None:
            # No exception - execute all operations
            for op in self._operations:
                try:
                    op()
                except Exception as e:
                    logger.error(f"Error in cache context operation: {e}")

    def set(self, key: str, payload: Any, tags: Set[str], ttl: Optional[int] = None):
        """
        Queue a set operation.

        Args:
            key: Cache key
            payload: Value to cache
            tags: Cache tags
            ttl: Time-to-live
        """
        self._operations.append(
            lambda: self.cache.set_with_tags(key, payload, tags, ttl)
        )

    def invalidate(self, *tags: str):
        """
        Queue an invalidation operation.

        Args:
            *tags: Tags to invalidate
        """
        self._operations.append(
            lambda: self.cache.invalidate_tags(*tags)
        )


def warm_cache(
    entities: List[Any],
    key_func: Callable[[Any], str],
    tags_func: Callable[[Any], Set[str]],
    serialize_func: Callable[[Any], dict],
    cache: Cache,
    ttl: Optional[int] = None
):
    """
    Warm cache with multiple entities at once.

    Useful for preloading cache after bulk operations or during startup.

    Args:
        entities: List of entities to cache
        key_func: Function to generate cache key for each entity
                  Signature: (entity) -> str
        tags_func: Function to generate tags for each entity
                   Signature: (entity) -> Set[str]
        serialize_func: Function to serialize entity to dict
                        Signature: (entity) -> dict
        cache: Cache instance
        ttl: Time-to-live in seconds

    Example:
        >>> organizations = db.query(Organization).all()
        >>> warm_cache(
        ...     entities=organizations,
        ...     key_func=lambda org: cache.key("organization", org.id),
        ...     tags_func=lambda org: {f"org:{org.id}", "org:list"},
        ...     serialize_func=_serialize_entity,
        ...     cache=cache,
        ...     ttl=3600
        ... )
    """
    with CacheContext(cache) as ctx:
        for entity in entities:
            try:
                key = key_func(entity)
                tags = tags_func(entity)
                payload = serialize_func(entity)
                ctx.set(key, payload, tags, ttl)
            except Exception as e:
                logger.error(f"Error warming cache for entity: {e}")
