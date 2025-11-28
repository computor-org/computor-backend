"""
Business logic for course member grading statistics.

This module provides the business logic for calculating and returning
aggregated progress statistics for course members.
"""

import logging
from typing import Optional, List
from uuid import UUID

from sqlalchemy.orm import Session

from computor_backend.api.exceptions import NotFoundException, ForbiddenException
from computor_backend.permissions.principal import Principal
from computor_backend.permissions.core import check_course_permissions
from computor_backend.cache import Cache
from computor_backend.repositories.course_member_gradings import (
    CourseMemberGradingsRepository,
    calculate_grading_stats,
    calculate_grading_stats_for_all_members,
)
from computor_backend.model.course import CourseMember, Course

from computor_types.course_member_gradings import (
    CourseMemberGradingsGet,
    CourseMemberGradingsList,
    CourseMemberGradingsQuery,
    CourseMemberGradingNode,
    ContentTypeGradingStats,
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
        params: Query parameters for filtering
        db: Database session
        cache: Optional cache instance

    Returns:
        CourseMemberGradingsGet with full grading statistics

    Raises:
        NotFoundException: If course member not found
        ForbiddenException: If user doesn't have access
    """
    # Get the course member
    course_member = db.query(CourseMember).filter(
        CourseMember.id == course_member_id
    ).first()

    if course_member is None:
        raise NotFoundException(detail=f"Course member {course_member_id} not found")

    # Determine course_id
    course_id = params.course_id or str(course_member.course_id)

    # Check if course_id matches the member's course
    if str(course_member.course_id) != course_id:
        raise NotFoundException(
            detail=f"Course member {course_member_id} is not a member of course {course_id}"
        )

    # Permission check:
    # - Lecturer or higher role (_lecturer, _maintainer, _owner) can access members in their courses
    # - Admin can access any member (handled by check_course_permissions)
    #
    # Use check_course_permissions with "_lecturer" role - this uses the role hierarchy
    # which automatically includes _maintainer, _owner, and admins
    user_id = permissions.get_user_id()

    # Check if user has lecturer or higher permissions for this course
    has_course_perms = check_course_permissions(
        permissions, CourseMember, "_lecturer", db
    ).filter(
        CourseMember.course_id == course_id,
        CourseMember.user_id == user_id
    ).first()

    if not has_course_perms:
        raise ForbiddenException(
            detail="You don't have permission to view this course member's grading statistics. "
                   "Lecturer role or higher is required."
        )

    # Initialize repository
    repo = CourseMemberGradingsRepository(db)

    # Get submittable contents
    submittable_contents = repo.get_submittable_contents(
        course_id=course_id,
        path_prefix=params.path_prefix,
        course_content_type_id=params.course_content_type_id,
    )

    # Get submitted contents for this member
    submitted_contents = repo.get_submitted_contents(
        course_member_id=course_member_id,
        course_id=course_id,
        path_prefix=params.path_prefix,
        course_content_type_id=params.course_content_type_id,
    )

    # Get path titles
    path_titles = repo.get_path_titles(course_id)

    # Calculate aggregated statistics
    stats = calculate_grading_stats(
        submittable_contents=submittable_contents,
        submitted_contents=submitted_contents,
        path_titles=path_titles,
        max_depth=params.depth,
    )

    # Convert to DTOs
    by_content_type = [
        ContentTypeGradingStats(**ct_stats)
        for ct_stats in stats["by_content_type"]
    ]

    nodes = [
        CourseMemberGradingNode(
            path=node["path"],
            title=node["title"],
            max_assignments=node["max_assignments"],
            submitted_assignments=node["submitted_assignments"],
            progress_percentage=node["progress_percentage"],
            latest_submission_at=node["latest_submission_at"],
            by_content_type=[
                ContentTypeGradingStats(**ct)
                for ct in node["by_content_type"]
            ],
        )
        for node in stats["nodes"]
    ]

    return CourseMemberGradingsGet(
        course_member_id=str(course_member_id),
        course_id=course_id,
        total_max_assignments=stats["total_max_assignments"],
        total_submitted_assignments=stats["total_submitted_assignments"],
        overall_progress_percentage=stats["overall_progress_percentage"],
        latest_submission_at=stats["latest_submission_at"],
        by_content_type=by_content_type,
        nodes=nodes,
    )


async def list_course_member_gradings(
    course_id: UUID | str,
    permissions: Principal,
    params: CourseMemberGradingsQuery,
    db: Session,
    cache: Optional[Cache] = None,
) -> List[CourseMemberGradingsList]:
    """
    Calculate and return grading statistics for all course members in a course.

    This is an optimized batch operation that calculates stats for all members
    at once, avoiding N+1 queries.

    Args:
        course_id: The course ID (required)
        permissions: Current user permissions
        params: Query parameters for filtering
        db: Database session
        cache: Optional cache instance

    Returns:
        List of CourseMemberGradingsList with grading statistics per member

    Raises:
        NotFoundException: If course not found
        ForbiddenException: If user doesn't have access
    """
    # Verify course exists
    course = db.query(Course).filter(Course.id == course_id).first()
    if course is None:
        raise NotFoundException(detail=f"Course {course_id} not found")

    # Permission check:
    # - Lecturer or higher role (_lecturer, _maintainer, _owner) can access
    # - Admin can access any course (handled by check_course_permissions)
    user_id = permissions.get_user_id()

    has_course_perms = check_course_permissions(
        permissions, CourseMember, "_lecturer", db
    ).filter(
        CourseMember.course_id == course_id,
        CourseMember.user_id == user_id
    ).first()

    if not has_course_perms:
        raise ForbiddenException(
            detail="You don't have permission to view course member grading statistics. "
                   "Lecturer role or higher is required."
        )

    # Initialize repository
    repo = CourseMemberGradingsRepository(db)

    # Get all course members (students only)
    course_members = repo.get_all_course_members_with_students_role(course_id)

    if not course_members:
        return []

    # Get submittable contents (same for all members)
    submittable_contents = repo.get_submittable_contents(
        course_id=course_id,
        path_prefix=params.path_prefix,
        course_content_type_id=params.course_content_type_id,
    )

    if not submittable_contents:
        # No submittable contents, return empty stats for all members
        return [
            CourseMemberGradingsList(
                course_member_id=member["course_member_id"],
                course_id=str(course_id),
                user_id=member.get("user_id"),
                username=member.get("username"),
                given_name=member.get("given_name"),
                family_name=member.get("family_name"),
                total_max_assignments=0,
                total_submitted_assignments=0,
                overall_progress_percentage=0.0,
                latest_submission_at=None,
                by_content_type=[],
            )
            for member in course_members
        ]

    # Get all submitted contents for all members in one query
    all_submitted_contents = repo.get_all_submitted_contents_for_course(
        course_id=course_id,
        path_prefix=params.path_prefix,
        course_content_type_id=params.course_content_type_id,
    )

    # Calculate stats for all members
    all_stats = calculate_grading_stats_for_all_members(
        submittable_contents=submittable_contents,
        all_submitted_contents=all_submitted_contents,
        course_members=course_members,
    )

    # Convert to DTOs
    return [
        CourseMemberGradingsList(
            course_member_id=stats["course_member_id"],
            course_id=str(course_id),
            user_id=stats.get("user_id"),
            username=stats.get("username"),
            given_name=stats.get("given_name"),
            family_name=stats.get("family_name"),
            total_max_assignments=stats["total_max_assignments"],
            total_submitted_assignments=stats["total_submitted_assignments"],
            overall_progress_percentage=stats["overall_progress_percentage"],
            latest_submission_at=stats["latest_submission_at"],
            by_content_type=[
                ContentTypeGradingStats(**ct)
                for ct in stats["by_content_type"]
            ],
        )
        for stats in all_stats
    ]
