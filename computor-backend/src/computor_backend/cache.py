"""
Write-through cache implementation with tag-based invalidation.

This module provides the core caching infrastructure for the Computor application,
implementing write-through caching with Redis backend and sophisticated tag-based
invalidation strategies.
"""

import hashlib
import logging
from typing import Any, Iterable, Optional, Callable, Dict
from datetime import datetime, date
import json

try:
    import orjson

    def _dumps(o: Any) -> bytes:
        """Serialize object with datetime support using orjson."""
        try:
            # orjson handles datetime natively with OPT_PASSTHROUGH_DATETIME or default handler
            return orjson.dumps(o, option=orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_PASSTHROUGH_DATETIME)
        except TypeError:
            # Fallback: convert datetime objects manually
            return orjson.dumps(_convert_datetime(o))

    _loads = lambda b: orjson.loads(b) if b else None
except ImportError:
    def _dumps(o: Any) -> bytes:
        """Serialize object with datetime support using standard json."""
        return json.dumps(_convert_datetime(o)).encode()

    _loads = lambda b: json.loads(b) if b else None


def _convert_datetime(obj: Any) -> Any:
    """
    Recursively convert datetime and custom objects to JSON-serializable types.

    This ensures datetime objects and custom types (like Ltree) can be serialized to JSON.
    """
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: _convert_datetime(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_convert_datetime(item) for item in obj]
    # Handle Ltree and other custom types from computor_backend.custom_types
    elif hasattr(obj, '__str__') and type(obj).__module__.startswith('computor_backend.custom_types'):
        return str(obj)
    # Handle sqlalchemy_utils types (like Ltree from sqlalchemy_utils)
    elif type(obj).__module__.startswith('sqlalchemy_utils'):
        return str(obj)
    return obj

import redis

logger = logging.getLogger(__name__)


def _stable_key(obj: Any) -> str:
    """
    Generate stable hash for complex objects.

    Used for complex IDs or parameter mappings that need to be part of cache keys.

    Args:
        obj: Any object that can be JSON-serialized

    Returns:
        SHA-1 hex digest of the canonical JSON representation
    """
    try:
        raw = orjson.dumps(obj, option=orjson.OPT_SORT_KEYS)
    except:
        import json
        raw = json.dumps(obj, sort_keys=True).encode()

    return hashlib.sha1(raw).hexdigest()


class Cache:
    """
    Write-through cache with tag-based invalidation.

    Features:
    - Simple key-value caching with TTL
    - Tag-based invalidation for related cache entries
    - Generational caching for high-fanout scenarios
    - Hierarchical key naming for debugging

    Example:
        >>> cache = Cache(redis_client, prefix="computor", default_ttl=600)
        >>>
        >>> # Simple get/set
        >>> cache.set_by_key("user:123", {"name": "John"})
        >>> user = cache.get_by_key("user:123")
        >>>
        >>> # With tags for invalidation
        >>> cache.set_with_tags(
        ...     "course:456",
        ...     course_data,
        ...     tags=["course:456", "org:789"],
        ...     ttl=3600
        ... )
        >>>
        >>> # Invalidate all cached entries with tag
        >>> cache.invalidate_tags("org:789")
    """

    def __init__(
        self,
        client: redis.Redis,
        prefix: str = "computor",
        default_ttl: int = 600
    ):
        """
        Initialize cache instance.

        Args:
            client: Redis client instance
            prefix: Key prefix for namespacing (e.g., "computor", "test")
            default_ttl: Default time-to-live in seconds (default: 600 = 10 minutes)
        """
        self.client = client
        self.prefix = prefix
        self.default_ttl = default_ttl
        self._stats = {
            "hits": 0,
            "misses": 0,
            "invalidations": 0,
            "sets": 0,
        }

    def k(self, *parts: str) -> str:
        """
        Build a namespaced key from parts.

        Args:
            *parts: Key components to join

        Returns:
            Full key with prefix: "{prefix}:{part1}:{part2}:..."

        Example:
            >>> cache.k("user", "123")
            'computor:user:123'
        """
        return f"{self.prefix}:" + ":".join(str(p) for p in parts)

    def key(self, kind: str, id_: Any) -> str:
        """
        Build a key for an entity.

        Args:
            kind: Entity type (e.g., "organization", "course")
            id_: Entity identifier (str, int, or complex dict/list)

        Returns:
            Full cache key

        Example:
            >>> cache.key("organization", "550e8400-e29b-41d4-a716-446655440000")
            'computor:organization:550e8400-e29b-41d4-a716-446655440000'

            >>> cache.key("query", {"filter": "active", "sort": "name"})
            'computor:query:a7b8c9d0e1f2...'
        """
        sid = id_ if isinstance(id_, (str, int)) else _stable_key(id_)
        return self.k(kind, sid)

    def get_by_key(self, key: str) -> Any:
        """
        Get value from cache by key.

        Args:
            key: Cache key

        Returns:
            Cached value (deserialized) or None if not found
        """
        try:
            value = self.client.get(key)
            if value is not None:
                self._stats["hits"] += 1
                logger.debug(f"Cache HIT: {key}")
                return _loads(value)
            else:
                self._stats["misses"] += 1
                logger.debug(f"Cache MISS: {key}")
                return None
        except Exception as e:
            logger.warning(f"Cache GET error for key {key}: {e}")
            self._stats["misses"] += 1
            return None

    def set_by_key(self, key: str, payload: Any, ttl: Optional[int] = None):
        """
        Set value in cache by key.

        Args:
            key: Cache key
            payload: Value to cache (will be JSON-serialized)
            ttl: Time-to-live in seconds (uses default_ttl if not specified)
        """
        try:
            self.client.setex(key, ttl or self.default_ttl, _dumps(payload))
            self._stats["sets"] += 1
            logger.debug(f"Cache SET: {key} (ttl={ttl or self.default_ttl}s)")
        except Exception as e:
            logger.error(f"Cache SET error for key {key}: {e}")

    def delete_by_key(self, key: str):
        """
        Delete a key from cache.

        Args:
            key: Cache key to delete
        """
        try:
            self.client.delete(key)
            logger.debug(f"Cache DELETE: {key}")
        except Exception as e:
            logger.error(f"Cache DELETE error for key {key}: {e}")

    # ========================================================================
    # Tag-Based Invalidation
    # ========================================================================

    def set_with_tags(
        self,
        key: str,
        payload: Any,
        tags: Iterable[str],
        ttl: Optional[int] = None
    ):
        """
        Set value in cache with associated tags for invalidation.

        Creates bidirectional mapping:
        - tag -> set of keys with this tag
        - key -> set of tags associated with this key

        Args:
            key: Cache key
            payload: Value to cache
            tags: Tags for grouping related cache entries
            ttl: Time-to-live in seconds

        Example:
            >>> cache.set_with_tags(
            ...     "course:456",
            ...     course_data,
            ...     tags=["course:456", "org:789", "course:list"],
            ...     ttl=1800
            ... )
        """
        tags = {t for t in tags if t}  # Remove None/empty tags

        if not tags:
            # No tags, just set normally
            self.set_by_key(key, payload, ttl)
            return

        try:
            p = self.client.pipeline()

            # Set the actual cached value
            p.setex(key, ttl or self.default_ttl, _dumps(payload))

            # Create tag -> keys mapping
            for t in tags:
                p.sadd(self.k("tag", t), key)

            # Create key -> tags mapping
            p.sadd(self.k("keytags", key), *tags)

            p.execute()
            self._stats["sets"] += 1
            logger.debug(f"Cache SET with tags: {key} tags={tags} (ttl={ttl or self.default_ttl}s)")
        except Exception as e:
            logger.error(f"Cache SET with tags error for key {key}: {e}")

    def invalidate_tags(self, *tags: str):
        """
        Invalidate all cache entries associated with given tags.

        This method:
        1. Finds all keys associated with each tag
        2. Deletes the keys
        3. Cleans up tag mappings

        Args:
            *tags: Tags to invalidate

        Example:
            >>> # Invalidate all organization-related caches
            >>> cache.invalidate_tags("org:789")
            >>>
            >>> # Invalidate multiple related entities
            >>> cache.invalidate_tags("org:789", "org:list", "course:family:123")
        """
        tags = {t for t in tags if t}
        if not tags:
            return

        try:
            p = self.client.pipeline()
            invalidated_keys = set()

            for t in tags:
                tagset_key = self.k("tag", t)
                keys_bytes = self.client.smembers(tagset_key)

                if not keys_bytes:
                    # No keys for this tag, just delete the tag set
                    p.delete(tagset_key)
                    continue

                # Convert bytes to strings
                keys = {k.decode() if isinstance(k, bytes) else k for k in keys_bytes}
                invalidated_keys.update(keys)

                # For each key: remove from all tag sets and delete key
                for key in keys:
                    keytags_key = self.k("keytags", key)
                    keytags_bytes = self.client.smembers(keytags_key)

                    # Remove key from all its tag sets
                    for kt in keytags_bytes:
                        kt_str = kt.decode() if isinstance(kt, bytes) else kt
                        p.srem(self.k("tag", kt_str), key)

                    # Delete key-to-tags mapping
                    p.delete(keytags_key)

                    # Delete the actual cached value
                    p.delete(key)

                # Delete tag set
                p.delete(tagset_key)

            p.execute()
            self._stats["invalidations"] += len(invalidated_keys)
            logger.info(f"Cache INVALIDATE: tags={tags} keys_deleted={len(invalidated_keys)}")
        except Exception as e:
            logger.error(f"Cache invalidation error for tags {tags}: {e}")

    def get_keys_for_tag(self, tag: str) -> set[str]:
        """
        Get all keys associated with a tag.

        Useful for debugging and monitoring.

        Args:
            tag: Tag name

        Returns:
            Set of cache keys associated with this tag
        """
        try:
            tagset_key = self.k("tag", tag)
            keys_bytes = self.client.smembers(tagset_key)
            return {k.decode() if isinstance(k, bytes) else k for k in keys_bytes}
        except Exception as e:
            logger.error(f"Error getting keys for tag {tag}: {e}")
            return set()

    # ========================================================================
    # Generational Caching (Advanced)
    # ========================================================================

    def tag_version(self, tag: str) -> int:
        """
        Get current version number for a tag.

        Args:
            tag: Tag name

        Returns:
            Current version number (0 if not set)
        """
        try:
            v = self.client.get(self.k("ver", tag))
            return int(v) if v else 0
        except Exception as e:
            logger.error(f"Error getting tag version for {tag}: {e}")
            return 0

    def bump_tag(self, tag: str) -> int:
        """
        Increment tag version number.

        This provides an efficient invalidation mechanism for high-fanout
        scenarios. Instead of deleting many keys, increment a version number.
        Keys that include the old version become effectively invalid.

        Args:
            tag: Tag name to increment

        Returns:
            New version number

        Example:
            >>> # Instead of invalidating thousands of dashboard keys
            >>> cache.bump_tag("dashboard")
            >>> # All keys containing old version are now stale
        """
        try:
            new_version = int(self.client.incr(self.k("ver", tag)))
            logger.info(f"Cache BUMP tag: {tag} -> v{new_version}")
            return new_version
        except Exception as e:
            logger.error(f"Error bumping tag version for {tag}: {e}")
            return 0

    def compose_versioned_key(self, base: str, *tags_with_version: str) -> str:
        """
        Compose a cache key that includes tag versions.

        The resulting key automatically becomes invalid when any of the
        tags are bumped, without requiring explicit invalidation.

        Args:
            base: Base key component (e.g., "dashboard:42:2025-10-01")
            *tags_with_version: Tags to include version numbers from

        Returns:
            Versioned cache key

        Example:
            >>> key = cache.compose_versioned_key(
            ...     "dashboard:user123:2025-10-03",
            ...     "org:789",
            ...     "course:456"
            ... )
            >>> # Result: "computor:v:{hash of base + org@v1 + course@v2}"
            >>>
            >>> # Later, when org changes:
            >>> cache.bump_tag("org:789")
            >>> # The key automatically becomes invalid
        """
        versions = [f"{t}@{self.tag_version(t)}" for t in tags_with_version]
        composite = {"base": base, "v": versions}
        return self.k("v", _stable_key(composite))

    # ========================================================================
    # Utilities
    # ========================================================================

    def clear_prefix(self):
        """
        Clear all keys with this cache's prefix.

        WARNING: This deletes ALL cached data for this prefix.
        Primarily useful for testing and development.
        """
        try:
            pattern = f"{self.prefix}:*"
            cursor = 0
            while True:
                cursor, keys = self.client.scan(cursor, match=pattern, count=100)
                if keys:
                    self.client.delete(*keys)
                if cursor == 0:
                    break
            logger.warning(f"Cache CLEARED: prefix={self.prefix}")
        except Exception as e:
            logger.error(f"Error clearing cache prefix {self.prefix}: {e}")

    def get_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dictionary with hit/miss/invalidation counts
        """
        hit_rate = 0.0
        if self._stats["hits"] + self._stats["misses"] > 0:
            hit_rate = self._stats["hits"] / (self._stats["hits"] + self._stats["misses"])

        return {
            **self._stats,
            "hit_rate": hit_rate,
        }

    def reset_stats(self):
        """Reset cache statistics counters."""
        self._stats = {
            "hits": 0,
            "misses": 0,
            "invalidations": 0,
            "sets": 0,
        }

    # ========================================================================
    # User View Caching (for VSCode extension endpoints)
    # ========================================================================

    def get_user_view(
        self,
        user_id: str,
        view_type: str,
        view_id: Optional[str] = None
    ) -> Optional[Any]:
        """
        Get cached user view data (for /students, /tutors, /lecturers endpoints).

        Args:
            user_id: User ID requesting the view
            view_type: Type of view (e.g., "courses", "course_contents", "course_members")
            view_id: Optional specific ID (e.g., course_id, course_content_id)

        Returns:
            Cached data or None if not found

        Example:
            >>> # Get student's courses list
            >>> cache.get_user_view("user123", "courses")
            >>>
            >>> # Get specific course content for student
            >>> cache.get_user_view("user123", "course_content", "content456")
        """
        if view_id:
            key = self.k("user_view", user_id, view_type, view_id)
        else:
            key = self.k("user_view", user_id, view_type)

        return self.get_by_key(key)

    def set_user_view(
        self,
        user_id: str,
        view_type: str,
        data: Any,
        view_id: Optional[str] = None,
        ttl: Optional[int] = None,
        related_ids: Optional[Dict[str, str]] = None
    ):
        """
        Cache user view data with proper tags for invalidation.

        Args:
            user_id: User ID requesting the view
            view_type: Type of view (e.g., "courses", "course_contents")
            data: Data to cache
            view_id: Optional specific ID
            ttl: Time-to-live (default: 300s for views)
            related_ids: Optional dict of related entity IDs for tag generation
                        e.g., {"course_id": "123", "org_id": "456"}

        Example:
            >>> # Cache student's courses list
            >>> cache.set_user_view(
            ...     user_id="user123",
            ...     view_type="courses",
            ...     data=courses_list,
            ...     ttl=300
            ... )
            >>>
            >>> # Cache specific course content with related IDs
            >>> cache.set_user_view(
            ...     user_id="user123",
            ...     view_type="course_content",
            ...     view_id="content456",
            ...     data=content_data,
            ...     related_ids={"course_id": "789", "course_family_id": "012"}
            ... )
        """
        if view_id:
            key = self.k("user_view", user_id, view_type, view_id)
        else:
            key = self.k("user_view", user_id, view_type)

        # Build tags for invalidation
        tags = {
            f"user:{user_id}",
            f"user:{user_id}:{view_type}",
            f"view:{view_type}",
        }

        if view_id:
            tags.add(f"user:{user_id}:{view_type}:{view_id}")

        # Add related entity tags for cascade invalidation
        if related_ids:
            for entity_type, entity_id in related_ids.items():
                tags.add(f"{entity_type}:{entity_id}")

        self.set_with_tags(
            key=key,
            payload=data,
            tags=tags,
            ttl=ttl or 300  # Default 5 minutes for user views
        )

    def invalidate_user_views(
        self,
        user_id: Optional[str] = None,
        view_type: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None
    ):
        """
        Invalidate user view caches with flexible targeting.

        Args:
            user_id: Invalidate all views for this user
            view_type: Invalidate specific view type across all users
            entity_type: Invalidate views related to entity type (e.g., "course")
            entity_id: Invalidate views related to specific entity

        Examples:
            >>> # Invalidate all views for a specific user
            >>> cache.invalidate_user_views(user_id="user123")
            >>>
            >>> # Invalidate all course views across all users
            >>> cache.invalidate_user_views(view_type="courses")
            >>>
            >>> # Invalidate all views related to a specific course
            >>> cache.invalidate_user_views(entity_type="course_id", entity_id="789")
            >>>
            >>> # Invalidate specific view type for a user
            >>> cache.invalidate_user_views(user_id="user123", view_type="courses")
        """
        tags_to_invalidate = []

        if user_id and view_type:
            tags_to_invalidate.append(f"user:{user_id}:{view_type}")
        elif user_id:
            tags_to_invalidate.append(f"user:{user_id}")
        elif view_type:
            tags_to_invalidate.append(f"view:{view_type}")

        if entity_type and entity_id:
            tags_to_invalidate.append(f"{entity_type}:{entity_id}")

        if tags_to_invalidate:
            self.invalidate_tags(*tags_to_invalidate)
            logger.info(f"Invalidated user views: user_id={user_id}, view_type={view_type}, "
                       f"entity={entity_type}:{entity_id if entity_id else 'all'}")
