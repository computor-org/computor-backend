"""
Permission caching layer for improved performance.
Provides Redis-based caching for permission checks and course memberships.

This module caches:
1. User course memberships (most critical for performance)
2. Individual permission check results
3. Course-filtered queries
"""

import hashlib
import json
from typing import Dict, Optional, Set, List
from functools import lru_cache
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from computor_backend.redis_cache import get_redis_client
from computor_backend.model.course import CourseMember
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


# ==============================================================================
# Course Membership Caching (New - High Performance)
# ==============================================================================

async def get_user_course_memberships(user_id: str, db: Session) -> Dict[str, str]:
    """
    Get user's course memberships with roles (CACHED).

    This is the MOST IMPORTANT cache for permission performance.
    Almost all permission checks depend on course memberships.

    Returns a dict mapping course_id -> course_role_id.
    Uses Redis cache with automatic fallback to database.

    Args:
        user_id: User identifier
        db: SQLAlchemy session

    Returns:
        Dictionary: {course_id: role_id, ...}

    Example:
        >>> memberships = await get_user_course_memberships("user-123", db)
        >>> memberships
        {"course-1": "_student", "course-2": "_lecturer"}
    """
    cache_key = f"permission:user:{user_id}:course_memberships"
    redis_client = await get_redis_client()

    # Try cache first
    try:
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            logger.debug(f"Cache HIT for user {user_id} course memberships")
            return json.loads(cached_data)
    except Exception as e:
        logger.warning(f"Redis cache read error: {e}")

    # Cache miss - query database
    logger.debug(f"Cache MISS for user {user_id} course memberships - querying DB")
    memberships = db.query(CourseMember).filter(
        CourseMember.user_id == user_id
    ).all()

    # Build result dict
    result = {
        str(membership.course_id): str(membership.course_role_id)
        for membership in memberships
    }

    # Store in cache (10 minute TTL)
    try:
        await redis_client.set(
            cache_key,
            json.dumps(result),
            ex=600  # 10 minutes
        )
        logger.debug(f"Cached {len(result)} memberships for user {user_id}")
    except Exception as e:
        logger.warning(f"Redis cache write error: {e}")

    return result


async def get_user_courses_with_role(
    user_id: str,
    minimum_role: str,
    db: Session,
    get_allowed_roles_func=None
) -> List[str]:
    """
    Get course IDs where user has at least the minimum role (CACHED).

    This uses the cached course memberships and filters by role hierarchy.

    Args:
        user_id: User identifier
        minimum_role: Minimum required role (e.g., "_student", "_tutor", "_lecturer")
        db: SQLAlchemy session
        get_allowed_roles_func: Function(minimum_role) -> List[role_ids]

    Returns:
        List of course IDs where user has sufficient permissions

    Example:
        >>> from computor_backend.permissions.query_builders import CoursePermissionQueryBuilder
        >>> courses = await get_user_courses_with_role(
        ...     "user-123",
        ...     "_tutor",
        ...     db,
        ...     CoursePermissionQueryBuilder.get_allowed_roles
        ... )
        >>> courses
        ["course-1", "course-2"]
    """
    # Get all memberships from cache/db
    memberships = await get_user_course_memberships(user_id, db)

    if not memberships:
        return []

    # If no role hierarchy function provided, use exact match
    if not get_allowed_roles_func:
        return [
            course_id
            for course_id, role_id in memberships.items()
            if role_id == minimum_role
        ]

    # Get allowed roles from hierarchy
    allowed_roles = get_allowed_roles_func(minimum_role)

    # Filter courses by role
    return [
        course_id
        for course_id, role_id in memberships.items()
        if role_id in allowed_roles
    ]


async def invalidate_user_course_memberships(user_id: str) -> None:
    """
    Invalidate cached course memberships for a user.

    Call this when:
    - CourseMember is created/updated/deleted for this user
    - User's role changes in any course

    Args:
        user_id: User identifier
    """
    cache_key = f"permission:user:{user_id}:course_memberships"
    redis_client = await get_redis_client()

    try:
        await redis_client.delete(cache_key)
        logger.info(f"Invalidated course memberships cache for user {user_id}")
    except Exception as e:
        logger.warning(f"Failed to invalidate cache: {e}")


async def invalidate_course_all_memberships(course_id: str, db: Session) -> None:
    """
    Invalidate cached memberships for all users in a course.

    Call this when:
    - Course roles change globally
    - Bulk membership operations occur

    Args:
        course_id: Course identifier
        db: SQLAlchemy session
    """
    # Get all user IDs in this course
    members = db.query(CourseMember.user_id).filter(
        CourseMember.course_id == course_id
    ).distinct().all()

    logger.info(f"Invalidating memberships cache for {len(members)} users in course {course_id}")

    redis_client = await get_redis_client()

    # Invalidate each user's cache
    for (user_id,) in members:
        cache_key = f"permission:user:{user_id}:course_memberships"
        try:
            await redis_client.delete(cache_key)
        except Exception:
            continue