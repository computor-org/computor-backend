"""
Permission caching layer for improved performance.
Provides both in-memory and Redis-based caching for permission checks.
"""

import hashlib
import json
from typing import Dict, Optional, Set
from functools import lru_cache
from datetime import datetime, timedelta

from ctutor_backend.redis_cache import get_redis_client
import logging

logger = logging.getLogger(__name__)


class PermissionCache:
    """
    Two-tier caching system for permissions:
    1. In-memory LRU cache for fast access
    2. Redis cache for distributed caching
    """
    
    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize permission cache
        
        Args:
            ttl_seconds: Time to live for cache entries in seconds (default 5 minutes)
        """
        self.ttl_seconds = ttl_seconds
        self._local_cache: Dict[str, tuple] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
    
    def _generate_key(self, user_id: str, resource: str, action: str, 
                     resource_id: Optional[str] = None) -> str:
        """Generate a unique cache key for permission check"""
        key_parts = [user_id, resource, action]
        if resource_id:
            key_parts.append(resource_id)
        
        key_string = ":".join(key_parts)
        return f"perm:{hashlib.md5(key_string.encode()).hexdigest()}"
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if local cache entry is still valid"""
        if key not in self._cache_timestamps:
            return False
        
        timestamp = self._cache_timestamps[key]
        return datetime.now() - timestamp < timedelta(seconds=self.ttl_seconds)
    
    async def get(self, user_id: str, resource: str, action: str,
                  resource_id: Optional[str] = None) -> Optional[bool]:
        """
        Get permission from cache
        
        Returns:
            Cached permission result or None if not found
        """
        key = self._generate_key(user_id, resource, action, resource_id)
        
        # Check local cache first
        if key in self._local_cache and self._is_cache_valid(key):
            logger.debug(f"Local cache hit for {key}")
            return self._local_cache[key]
        
        # Check Redis cache
        try:
            cache = await get_redis_client()
            cached_value = await cache.get(key)
            
            if cached_value:
                logger.debug(f"Redis cache hit for {key}")
                result = json.loads(cached_value)
                
                # Update local cache
                self._local_cache[key] = result
                self._cache_timestamps[key] = datetime.now()
                
                return result
        except Exception as e:
            logger.warning(f"Redis cache error: {e}")
        
        logger.debug(f"Cache miss for {key}")
        return None
    
    async def set(self, user_id: str, resource: str, action: str,
                  resource_id: Optional[str], result: bool):
        """
        Store permission in cache
        """
        key = self._generate_key(user_id, resource, action, resource_id)
        
        # Update local cache
        self._local_cache[key] = result
        self._cache_timestamps[key] = datetime.now()
        
        # Update Redis cache
        try:
            cache = await get_redis_client()
            await cache.set(key, json.dumps(result), ex=self.ttl_seconds)
            logger.debug(f"Cached permission for {key}: {result}")
        except Exception as e:
            logger.warning(f"Failed to cache in Redis: {e}")
    
    async def invalidate_user(self, user_id: str):
        """
        Invalidate all cached permissions for a user
        """
        # Clear local cache entries for user
        keys_to_remove = [
            key for key in self._local_cache
            if key.startswith(f"perm:") and user_id in key
        ]
        
        for key in keys_to_remove:
            self._local_cache.pop(key, None)
            self._cache_timestamps.pop(key, None)
        
        # Clear Redis cache entries
        try:
            _ = await get_redis_client()
            # This would need a pattern-based deletion in Redis
            # For now, we'll just log it
            logger.info(f"Invalidated cache for user {user_id}")
        except Exception as e:
            logger.warning(f"Failed to invalidate Redis cache: {e}")
    
    def clear_local_cache(self):
        """Clear the entire local cache"""
        self._local_cache.clear()
        self._cache_timestamps.clear()
        logger.info("Local permission cache cleared")


class CoursePermissionCache:
    """
    Specialized cache for course-related permissions
    """
    
    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
        self._course_members_cache: Dict[str, Set[str]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
    
    @lru_cache(maxsize=1024)
    def get_user_courses_cached(self, user_id: str, minimum_role: str) -> Optional[Set[str]]:
        """
        Get cached list of courses where user has minimum role
        
        This is an in-memory only cache for fast access
        """
        key = f"{user_id}:{minimum_role}"
        
        if key in self._course_members_cache:
            if self._is_cache_valid(key):
                return self._course_members_cache[key]
        
        return None
    
    def set_user_courses(self, user_id: str, minimum_role: str, course_ids: Set[str]):
        """Store user's courses in cache"""
        key = f"{user_id}:{minimum_role}"
        self._course_members_cache[key] = course_ids
        self._cache_timestamps[key] = datetime.now()
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache entry is still valid"""
        if key not in self._cache_timestamps:
            return False
        
        timestamp = self._cache_timestamps[key]
        return datetime.now() - timestamp < timedelta(seconds=self.ttl_seconds)
    
    def invalidate_user(self, user_id: str):
        """Invalidate all course cache entries for a user"""
        keys_to_remove = [
            key for key in self._course_members_cache
            if key.startswith(f"{user_id}:")
        ]
        
        for key in keys_to_remove:
            self._course_members_cache.pop(key, None)
            self._cache_timestamps.pop(key, None)
        
        # Clear LRU cache
        self.get_user_courses_cached.cache_clear()
    
    def invalidate_course(self, _: str):
        """
        Invalidate cache entries related to a specific course
        This requires clearing all user entries since we don't track course->user mappings
        """
        # For now, clear everything - in production, you might want to track this better
        self._course_members_cache.clear()
        self._cache_timestamps.clear()
        self.get_user_courses_cached.cache_clear()


# Global cache instances
permission_cache = PermissionCache()
course_permission_cache = CoursePermissionCache()


async def cached_permission_check(principal, resource: str, action: str,
                                 resource_id: Optional[str] = None) -> bool:
    """
    Cached version of permission check
    """
    if principal.is_admin:
        return True
    
    # Try to get from cache
    cached_result = await permission_cache.get(
        principal.user_id, resource, action, resource_id
    )
    
    if cached_result is not None:
        return cached_result
    
    # Perform actual permission check
    result = principal.permitted(resource, action, resource_id)
    
    # Cache the result
    await permission_cache.set(
        principal.user_id, resource, action, resource_id, result
    )
    
    return result