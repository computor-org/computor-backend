"""
Course-membership permission caching.

Caches user course memberships in Redis (the hottest lookup in permission
checks) and provides the matching invalidation helpers.
"""

import json
from typing import Dict, List
from sqlalchemy.orm import Session

from computor_backend.redis_cache import get_redis_client
from computor_backend.model.course import CourseMember
import logging

logger = logging.getLogger(__name__)


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