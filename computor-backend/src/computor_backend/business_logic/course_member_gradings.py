"""
Business logic for course member grading statistics.

This module provides the business logic for calculating and returning
aggregated progress statistics for course members.

Delegates to CourseMemberGradingsViewRepository for consistent caching pattern.
"""

import logging
from typing import Optional, List
from uuid import UUID

from sqlalchemy.orm import Session

from computor_backend.permissions.principal import Principal
from computor_backend.cache import Cache
from computor_backend.repositories.course_member_gradings_view import (
    CourseMemberGradingsViewRepository,
)
from computor_backend.services.course_member_grading_stats import (
    aggregate_grading_status as _aggregate_grading_status,  # noqa: F401
    process_hierarchical_stats as _process_hierarchical_stats,  # noqa: F401
)

from computor_types.course_member_gradings import (
    CourseMemberGradingsGet,
    CourseMemberGradingsList,
    CourseMemberGradingsQuery,
)

logger = logging.getLogger(__name__)


async def get_course_member_gradings(
    course_member_id: UUID | str,
    permissions: Principal,
    params: CourseMemberGradingsQuery,
    db: Session,
    cache: Optional[Cache] = None,
) -> CourseMemberGradingsGet:
    """
    Calculate and return grading statistics for a course member.

    This endpoint calculates:
    - Maximum assignments available vs. submitted assignments
    - Breakdown by course_content_type
    - Percentage calculations at each hierarchical level
    - Latest submission date per aggregation level

    Args:
        course_member_id: The course member ID to get stats for
        permissions: Current user permissions
        params: Query parameters
        db: Database session (unused, kept for API compatibility)
        cache: Optional cache instance

    Returns:
        CourseMemberGradingsGet with full grading statistics

    Raises:
        NotFoundException: If course member not found
        ForbiddenException: If user doesn't have access
    """
    # Delegate to ViewRepository for consistent caching pattern
    repo = CourseMemberGradingsViewRepository(cache=cache, user_id=permissions.get_user_id())
    try:
        return await repo.get_course_member_gradings(course_member_id, permissions, params)
    finally:
        repo.close()


async def list_course_member_gradings(
    course_id: UUID | str,
    permissions: Principal,
    params: CourseMemberGradingsQuery,
    db: Session,
    cache: Optional[Cache] = None,
) -> List[CourseMemberGradingsList]:
    """
    Calculate and return grading statistics for all course members in a course.

    This is an optimized batch operation that leverages per-student caching.

    Args:
        course_id: The course ID (required)
        permissions: Current user permissions
        params: Query parameters
        db: Database session (unused, kept for API compatibility)
        cache: Optional cache instance

    Returns:
        List of CourseMemberGradingsList with grading statistics per member

    Raises:
        NotFoundException: If course not found
        ForbiddenException: If user doesn't have access
    """
    # Delegate to ViewRepository for consistent caching pattern
    repo = CourseMemberGradingsViewRepository(cache=cache, user_id=permissions.get_user_id())
    try:
        return await repo.list_course_member_gradings(course_id, permissions, params)
    finally:
        repo.close()
