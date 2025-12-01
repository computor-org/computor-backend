"""
Business logic for course member grading statistics.

This module provides the business logic for calculating and returning
aggregated progress statistics for course members.

Delegates to CourseMemberGradingsViewRepository for consistent caching pattern.
"""

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from collections import defaultdict

from sqlalchemy.orm import Session

from computor_backend.api.exceptions import NotFoundException, ForbiddenException
from computor_backend.permissions.principal import Principal
from computor_backend.cache import Cache
from computor_backend.repositories.course_member_gradings_view import (
    CourseMemberGradingsViewRepository,
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


def _process_hierarchical_stats(
    db_stats: List[Dict[str, Any]],
    path_titles: Dict[str, str],
) -> Dict[str, Any]:
    """
    Process raw database statistics into hierarchical structure.

    This function takes the flat SQL results with ltree paths and aggregates
    them into a nested structure with percentage calculations.

    Args:
        db_stats: Raw database query results
        path_titles: Mapping of ltree paths to display titles

    Returns:
        Dictionary with:
        - total_max_assignments: Total maximum assignments
        - total_submitted_assignments: Total submitted assignments
        - overall_progress_percentage: Overall progress percentage
        - latest_submission_at: Latest submission timestamp
        - by_content_type: List of content type breakdowns
        - nodes: List of hierarchical node breakdowns
    """
    if not db_stats:
        return {
            "total_max_assignments": 0,
            "total_submitted_assignments": 0,
            "overall_progress_percentage": 0.0,
            "latest_submission_at": None,
            "by_content_type": [],
            "nodes": [],
        }

    # Group by content_type_id for top-level breakdown
    by_content_type = defaultdict(lambda: {"max": 0, "submitted": 0})
    by_node = {}  # path -> stats

    total_max = 0
    total_submitted = 0
    latest_submission = None

    for row in db_stats:
        path = row["path"]
        content_type_id = row.get("content_type_id")
        content_type_title = row.get("content_type_title", "Unknown")
        max_assignments = row["max_assignments"]
        submitted_assignments = row["submitted_assignments"]
        latest_at = row.get("latest_submission_at")

        # Aggregate by content type
        if content_type_id:
            by_content_type[content_type_id]["max"] += max_assignments
            by_content_type[content_type_id]["submitted"] += submitted_assignments
            by_content_type[content_type_id]["title"] = content_type_title
            by_content_type[content_type_id]["id"] = content_type_id

        # Aggregate by node (path)
        if path not in by_node:
            by_node[path] = {
                "path": path,
                "title": path_titles.get(path, path),
                "max_assignments": 0,
                "submitted_assignments": 0,
                "latest_submission_at": None,
                "by_content_type": defaultdict(lambda: {"max": 0, "submitted": 0}),
            }

        by_node[path]["max_assignments"] += max_assignments
        by_node[path]["submitted_assignments"] += submitted_assignments

        if latest_at:
            if by_node[path]["latest_submission_at"] is None or latest_at > by_node[path]["latest_submission_at"]:
                by_node[path]["latest_submission_at"] = latest_at

        # Store content type breakdown per node
        if content_type_id:
            by_node[path]["by_content_type"][content_type_id]["max"] += max_assignments
            by_node[path]["by_content_type"][content_type_id]["submitted"] += submitted_assignments
            by_node[path]["by_content_type"][content_type_id]["title"] = content_type_title
            by_node[path]["by_content_type"][content_type_id]["id"] = content_type_id

        # Track overall totals
        total_max += max_assignments
        total_submitted += submitted_assignments

        if latest_at:
            if latest_submission is None or latest_at > latest_submission:
                latest_submission = latest_at

    # Convert content type aggregations to list format
    content_type_list = [
        {
            "content_type_id": ct_id,
            "content_type_title": ct_data["title"],
            "max_assignments": ct_data["max"],
            "submitted_assignments": ct_data["submitted"],
            "progress_percentage": round(
                (ct_data["submitted"] / ct_data["max"] * 100) if ct_data["max"] > 0 else 0.0,
                2
            ),
        }
        for ct_id, ct_data in by_content_type.items()
    ]

    # Convert node aggregations to list format
    node_list = []
    for path, node_data in by_node.items():
        # Convert node's content type breakdown
        node_ct_list = [
            {
                "content_type_id": ct_id,
                "content_type_title": ct_data["title"],
                "max_assignments": ct_data["max"],
                "submitted_assignments": ct_data["submitted"],
                "progress_percentage": round(
                    (ct_data["submitted"] / ct_data["max"] * 100) if ct_data["max"] > 0 else 0.0,
                    2
                ),
            }
            for ct_id, ct_data in node_data["by_content_type"].items()
        ]

        node_list.append({
            "path": path,
            "title": node_data["title"],
            "max_assignments": node_data["max_assignments"],
            "submitted_assignments": node_data["submitted_assignments"],
            "progress_percentage": round(
                (node_data["submitted_assignments"] / node_data["max_assignments"] * 100)
                if node_data["max_assignments"] > 0 else 0.0,
                2
            ),
            "latest_submission_at": node_data["latest_submission_at"],
            "by_content_type": node_ct_list,
        })

    # Calculate overall progress
    overall_progress = round(
        (total_submitted / total_max * 100) if total_max > 0 else 0.0,
        2
    )

    return {
        "total_max_assignments": total_max,
        "total_submitted_assignments": total_submitted,
        "overall_progress_percentage": overall_progress,
        "latest_submission_at": latest_submission,
        "by_content_type": content_type_list,
        "nodes": node_list,
    }
