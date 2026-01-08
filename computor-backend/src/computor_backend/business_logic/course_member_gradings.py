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


def _aggregate_grading_status(statuses: List[str]) -> str:
    """
    Aggregate multiple grading statuses following priority rules.

    Rules:
    1. If ANY 'correction_necessary' exists -> 'correction_necessary'
    2. Else if ANY 'improvement_possible' exists -> 'improvement_possible'
    3. Else if ALL are 'corrected' -> 'corrected'
    4. Else -> 'not_reviewed' (mix of corrected/not_reviewed, or all not_reviewed)

    Args:
        statuses: List of grading status strings

    Returns:
        Aggregated status string
    """
    if not statuses:
        return "not_reviewed"

    # Check for correction_necessary (highest priority)
    if "correction_necessary" in statuses:
        return "correction_necessary"

    # Check for improvement_possible
    if "improvement_possible" in statuses:
        return "improvement_possible"

    # Check if ALL are corrected
    if all(s == "corrected" for s in statuses):
        return "corrected"

    # Default: not_reviewed (mix or all not_reviewed)
    return "not_reviewed"


def _process_hierarchical_stats(
    db_stats: List[Dict[str, Any]],
    path_info: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Process raw database statistics into hierarchical structure.

    This function takes the flat SQL results with ltree paths and aggregates
    them into a nested structure with percentage calculations.

    Args:
        db_stats: Raw database query results
        path_info: Mapping of ltree paths to info dict (title, course_content_kind_id, submittable)
                   Can also be a simple Dict[str, str] for backwards compatibility (just titles)

    Returns:
        Dictionary with:
        - total_max_assignments: Total maximum assignments
        - total_submitted_assignments: Total submitted assignments
        - overall_progress_percentage: Overall progress percentage
        - latest_submission_at: Latest submission timestamp
        - overall_average_grading: Course-level average grade (0.0-1.0)
        - by_content_type: List of content type breakdowns
        - nodes: List of hierarchical node breakdowns
    """
    if not db_stats:
        return {
            "total_max_assignments": 0,
            "total_submitted_assignments": 0,
            "overall_progress_percentage": 0.0,
            "latest_submission_at": None,
            "overall_average_grading": None,
            "by_content_type": [],
            "nodes": [],
        }

    # Group by content_type_id for top-level breakdown
    by_content_type = defaultdict(lambda: {"max": 0, "submitted": 0, "graded": 0, "grade_sum": 0.0})
    by_node = {}  # path -> stats

    total_max = 0
    total_submitted = 0
    total_graded = 0
    total_grade_sum = 0.0
    latest_submission = None

    for row in db_stats:
        path = row["path"]
        content_type_id = row.get("content_type_id")
        content_type_slug = row.get("content_type_slug", "")
        content_type_title = row.get("content_type_title")
        content_type_color = row.get("content_type_color")
        max_assignments = row["max_assignments"]
        submitted_assignments = row["submitted_assignments"]
        latest_at = row.get("latest_submission_at")
        # Grading statistics from DB
        graded_assignments = row.get("graded_assignments", 0) or 0
        average_grading = row.get("average_grading")
        grading_status = row.get("grading_status")

        # Aggregate by content type
        if content_type_id:
            by_content_type[content_type_id]["max"] += max_assignments
            by_content_type[content_type_id]["submitted"] += submitted_assignments
            by_content_type[content_type_id]["graded"] += graded_assignments
            if average_grading is not None and graded_assignments > 0:
                by_content_type[content_type_id]["grade_sum"] += average_grading * graded_assignments
            by_content_type[content_type_id]["id"] = content_type_id
            by_content_type[content_type_id]["slug"] = content_type_slug
            by_content_type[content_type_id]["title"] = content_type_title
            by_content_type[content_type_id]["color"] = content_type_color

        # Aggregate by node (path)
        if path not in by_node:
            # Handle both old format (just titles) and new format (full info dict)
            if path in path_info:
                info = path_info[path]
                if isinstance(info, dict):
                    # New format with full info
                    title = info.get("title", path)
                    submittable = info.get("submittable")
                    position = info.get("position")
                    course_content_type_color = info.get("course_content_type_color")
                else:
                    # Old format (just title string)
                    title = info
                    submittable = None
                    position = None
                    course_content_type_color = None
            else:
                title = path
                submittable = None
                position = None
                course_content_type_color = None

            by_node[path] = {
                "path": path,
                "title": title,
                "submittable": submittable,
                "position": position,
                "course_content_type_color": course_content_type_color,
                "max_assignments": 0,
                "submitted_assignments": 0,
                "graded_assignments": 0,
                "grade_sum": 0.0,
                "latest_submission_at": None,
                "by_content_type": defaultdict(lambda: {"max": 0, "submitted": 0, "graded": 0, "grade_sum": 0.0}),
                "grading_statuses": [],  # Collect all statuses for aggregation
            }

        by_node[path]["max_assignments"] += max_assignments
        by_node[path]["submitted_assignments"] += submitted_assignments
        by_node[path]["graded_assignments"] += graded_assignments
        if average_grading is not None and graded_assignments > 0:
            by_node[path]["grade_sum"] += average_grading * graded_assignments

        # Collect grading_status for later aggregation
        if grading_status is not None:
            by_node[path]["grading_statuses"].append(grading_status)

        if latest_at:
            if by_node[path]["latest_submission_at"] is None or latest_at > by_node[path]["latest_submission_at"]:
                by_node[path]["latest_submission_at"] = latest_at

        # Store content type breakdown per node
        if content_type_id:
            by_node[path]["by_content_type"][content_type_id]["max"] += max_assignments
            by_node[path]["by_content_type"][content_type_id]["submitted"] += submitted_assignments
            by_node[path]["by_content_type"][content_type_id]["graded"] += graded_assignments
            if average_grading is not None and graded_assignments > 0:
                by_node[path]["by_content_type"][content_type_id]["grade_sum"] += average_grading * graded_assignments
            by_node[path]["by_content_type"][content_type_id]["id"] = content_type_id
            by_node[path]["by_content_type"][content_type_id]["slug"] = content_type_slug
            by_node[path]["by_content_type"][content_type_id]["title"] = content_type_title
            by_node[path]["by_content_type"][content_type_id]["color"] = content_type_color

        # Track overall totals
        total_max += max_assignments
        total_submitted += submitted_assignments
        total_graded += graded_assignments
        if average_grading is not None and graded_assignments > 0:
            total_grade_sum += average_grading * graded_assignments

        if latest_at:
            if latest_submission is None or latest_at > latest_submission:
                latest_submission = latest_at

    # Convert content type aggregations to list format (use course_content_type_* field names for DTO)
    content_type_list = [
        {
            "course_content_type_id": ct_id,
            "course_content_type_slug": ct_data.get("slug", ""),
            "course_content_type_title": ct_data.get("title"),
            "course_content_type_color": ct_data.get("color"),
            "max_assignments": ct_data["max"],
            "submitted_assignments": ct_data["submitted"],
            "progress_percentage": round(
                (ct_data["submitted"] / ct_data["max"] * 100) if ct_data["max"] > 0 else 0.0,
                2
            ),
            "latest_submission_at": None,  # Not tracked at this level
            # Grading statistics
            "graded_assignments": ct_data["graded"],
            "average_grading": round(ct_data["grade_sum"] / ct_data["graded"], 4) if ct_data["graded"] > 0 else None,
        }
        for ct_id, ct_data in by_content_type.items()
    ]

    # Convert node aggregations to list format
    node_list = []
    for path, node_data in by_node.items():
        # Convert node's content type breakdown (use course_content_type_* field names for DTO)
        node_ct_list = [
            {
                "course_content_type_id": ct_id,
                "course_content_type_slug": ct_data.get("slug", ""),
                "course_content_type_title": ct_data.get("title"),
                "course_content_type_color": ct_data.get("color"),
                "max_assignments": ct_data["max"],
                "submitted_assignments": ct_data["submitted"],
                "progress_percentage": round(
                    (ct_data["submitted"] / ct_data["max"] * 100) if ct_data["max"] > 0 else 0.0,
                    2
                ),
                "latest_submission_at": None,  # Not tracked per content type per node
                # Grading statistics
                "graded_assignments": ct_data["graded"],
                "average_grading": round(ct_data["grade_sum"] / ct_data["graded"], 4) if ct_data["graded"] > 0 else None,
            }
            for ct_id, ct_data in node_data["by_content_type"].items()
        ]

        # Determine grading values based on whether this is a leaf node (submittable)
        # For submittable nodes (assignments): use grading (actual grade)
        # For non-submittable nodes (units): use average_grading (average of descendants)
        is_submittable = node_data.get("submittable", False)
        node_graded = node_data["graded_assignments"]
        node_avg = round(node_data["grade_sum"] / node_graded, 4) if node_graded > 0 else None

        # Determine grading_status using aggregation rules:
        # 1. If ANY CORRECTION_NECESSARY(2) -> CORRECTION_NECESSARY(2)
        # 2. Else if ANY IMPROVEMENT_POSSIBLE(3) -> IMPROVEMENT_POSSIBLE(3)
        # 3. Else if ALL are CORRECTED(1) -> CORRECTED(1)
        # 4. Else -> NOT_REVIEWED(0)
        node_grading_status = _aggregate_grading_status(node_data["grading_statuses"])

        node_list.append({
            "path": path,
            "title": node_data["title"],
            "submittable": node_data.get("submittable"),
            "position": node_data.get("position"),
            "course_content_type_color": node_data.get("course_content_type_color"),
            "max_assignments": node_data["max_assignments"],
            "submitted_assignments": node_data["submitted_assignments"],
            "progress_percentage": round(
                (node_data["submitted_assignments"] / node_data["max_assignments"] * 100)
                if node_data["max_assignments"] > 0 else 0.0,
                2
            ),
            "latest_submission_at": node_data["latest_submission_at"],
            "by_content_type": node_ct_list,
            # Grading statistics
            # For assignments: grading is the actual grade, average_grading is None
            # For units: grading is None, average_grading is the average of descendants
            "grading": node_avg if is_submittable else None,
            "average_grading": node_avg if not is_submittable else None,
            "graded_assignments": node_graded,
            "grading_status": node_grading_status,
        })

    # Calculate overall progress
    overall_progress = round(
        (total_submitted / total_max * 100) if total_max > 0 else 0.0,
        2
    )

    # Calculate overall average grading
    overall_avg_grading = round(total_grade_sum / total_graded, 4) if total_graded > 0 else None

    return {
        "total_max_assignments": total_max,
        "total_submitted_assignments": total_submitted,
        "overall_progress_percentage": overall_progress,
        "latest_submission_at": latest_submission,
        "overall_average_grading": overall_avg_grading,
        "by_content_type": content_type_list,
        "nodes": node_list,
    }
