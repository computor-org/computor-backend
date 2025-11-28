"""
Business logic for course member grading statistics.

This module provides the business logic for calculating and returning
aggregated progress statistics for course members.

Uses database-level aggregation for performance optimization.
"""

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from collections import defaultdict

from sqlalchemy.orm import Session

from computor_backend.api.exceptions import NotFoundException, ForbiddenException
from computor_backend.permissions.principal import Principal
from computor_backend.permissions.core import check_course_permissions
from computor_backend.cache import Cache
from computor_backend.repositories.course_member_gradings import (
    CourseMemberGradingsRepository,
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

    # Get hierarchical stats using database-level aggregation
    db_stats = repo.get_hierarchical_stats_for_member(
        course_member_id=course_member_id,
        course_id=course_id,
        path_prefix=params.path_prefix,
        course_content_type_id=params.course_content_type_id,
        max_depth=params.depth,
    )

    # Get path titles for display
    path_titles = repo.get_path_titles(course_id)

    # Process database results into the expected structure
    stats = _process_hierarchical_stats(db_stats, path_titles)

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

    # Get course-level stats for all members using database-level aggregation
    db_stats = repo.get_course_level_stats_for_all_members(
        course_id=course_id,
        path_prefix=params.path_prefix,
        course_content_type_id=params.course_content_type_id,
    )

    if not db_stats:
        # No stats - either no students or no submittable contents
        # Get all students to return empty stats
        course_members = repo.get_all_course_members_with_students_role(course_id)
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

    # Process database results: group by course_member_id
    all_stats = _process_course_level_stats_for_all_members(db_stats)

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


def _process_hierarchical_stats(
    db_stats: List[Dict[str, Any]],
    path_titles: Dict[str, str],
) -> Dict[str, Any]:
    """
    Process database-level hierarchical stats into the expected structure.

    The database returns one row per (path, content_type) combination.
    We need to aggregate these into nodes with by_content_type lists.

    Args:
        db_stats: Raw database results from get_hierarchical_stats_for_member
        path_titles: Dict mapping path to title

    Returns:
        Dict with aggregated statistics ready for DTO conversion
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

    # Group stats by path
    stats_by_path: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in db_stats:
        stats_by_path[row["path"]].append(row)

    # Track overall stats (aggregated from all paths at depth 1, or all rows if single level)
    # We need to find the root-level totals
    all_content_types: Dict[str, Dict[str, Any]] = {}
    overall_max = 0
    overall_submitted = 0
    overall_latest = None

    # Build nodes
    nodes = []
    for path, path_stats in stats_by_path.items():
        node_max = 0
        node_submitted = 0
        node_latest = None
        by_content_type = []

        for stat in path_stats:
            ct_max = stat["max_assignments"]
            ct_submitted = stat["submitted_assignments"]
            ct_latest = stat["latest_submission_at"]

            node_max += ct_max
            node_submitted += ct_submitted
            if ct_latest and (node_latest is None or ct_latest > node_latest):
                node_latest = ct_latest

            # Track content type info for overall aggregation
            ct_id = stat["content_type_id"]
            if ct_id not in all_content_types:
                all_content_types[ct_id] = {
                    "course_content_type_id": ct_id,
                    "course_content_type_slug": stat["content_type_slug"],
                    "course_content_type_title": stat["content_type_title"],
                    "course_content_type_color": stat["content_type_color"],
                }

            by_content_type.append({
                "course_content_type_id": ct_id,
                "course_content_type_slug": stat["content_type_slug"],
                "course_content_type_title": stat["content_type_title"],
                "course_content_type_color": stat["content_type_color"],
                "max_assignments": ct_max,
                "submitted_assignments": ct_submitted,
                "progress_percentage": (ct_submitted / ct_max * 100) if ct_max > 0 else 0.0,
                "latest_submission_at": ct_latest,
            })

        nodes.append({
            "path": path,
            "title": path_titles.get(path),
            "max_assignments": node_max,
            "submitted_assignments": node_submitted,
            "progress_percentage": (node_submitted / node_max * 100) if node_max > 0 else 0.0,
            "latest_submission_at": node_latest,
            "by_content_type": by_content_type,
        })

    # Sort nodes by depth then path
    nodes.sort(key=lambda n: (len(n["path"].split(".")), n["path"]))

    # Calculate overall totals from the deepest unique paths (leaf paths)
    # Actually, we need the totals from all unique content assignments
    # The database already gives us per-path aggregation, so we need to find
    # the deepest level stats (where all assignments are counted once)
    # For overall stats, we look at the deepest path level for each branch
    # But simpler: just use the first level (depth 1) stats summed up,
    # since that already aggregates everything beneath it

    # Find minimum depth and aggregate from those paths
    if nodes:
        min_depth = min(len(n["path"].split(".")) for n in nodes)
        root_nodes = [n for n in nodes if len(n["path"].split(".")) == min_depth]

        # Aggregate from root level nodes
        overall_by_content_type: Dict[str, Dict[str, Any]] = {}
        for node in root_nodes:
            overall_max += node["max_assignments"]
            overall_submitted += node["submitted_assignments"]
            if node["latest_submission_at"] and (overall_latest is None or node["latest_submission_at"] > overall_latest):
                overall_latest = node["latest_submission_at"]

            for ct in node["by_content_type"]:
                ct_id = ct["course_content_type_id"]
                if ct_id not in overall_by_content_type:
                    overall_by_content_type[ct_id] = {
                        "course_content_type_id": ct_id,
                        "course_content_type_slug": ct["course_content_type_slug"],
                        "course_content_type_title": ct["course_content_type_title"],
                        "course_content_type_color": ct["course_content_type_color"],
                        "max_assignments": 0,
                        "submitted_assignments": 0,
                        "latest_submission_at": None,
                    }
                overall_by_content_type[ct_id]["max_assignments"] += ct["max_assignments"]
                overall_by_content_type[ct_id]["submitted_assignments"] += ct["submitted_assignments"]
                ct_latest = ct["latest_submission_at"]
                if ct_latest:
                    existing_latest = overall_by_content_type[ct_id]["latest_submission_at"]
                    if existing_latest is None or ct_latest > existing_latest:
                        overall_by_content_type[ct_id]["latest_submission_at"] = ct_latest

        # Calculate percentages for overall by_content_type
        overall_by_ct_list = []
        for ct in overall_by_content_type.values():
            ct["progress_percentage"] = (ct["submitted_assignments"] / ct["max_assignments"] * 100) if ct["max_assignments"] > 0 else 0.0
            overall_by_ct_list.append(ct)
    else:
        overall_by_ct_list = []

    return {
        "total_max_assignments": overall_max,
        "total_submitted_assignments": overall_submitted,
        "overall_progress_percentage": (overall_submitted / overall_max * 100) if overall_max > 0 else 0.0,
        "latest_submission_at": overall_latest,
        "by_content_type": overall_by_ct_list,
        "nodes": nodes,
    }


def _process_course_level_stats_for_all_members(
    db_stats: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Process database-level course stats for all members into the expected structure.

    The database returns one row per (course_member, content_type) combination.
    We need to aggregate these into member stats with by_content_type lists.

    Args:
        db_stats: Raw database results from get_course_level_stats_for_all_members

    Returns:
        List of dicts with grading stats per course member
    """
    if not db_stats:
        return []

    # Group stats by course_member_id, preserving order
    seen_members = []
    stats_by_member: Dict[str, List[Dict[str, Any]]] = {}
    member_info: Dict[str, Dict[str, Any]] = {}

    for row in db_stats:
        member_id = row["course_member_id"]
        if member_id not in stats_by_member:
            seen_members.append(member_id)
            stats_by_member[member_id] = []
            member_info[member_id] = {
                "user_id": row["user_id"],
                "username": row["username"],
                "given_name": row["given_name"],
                "family_name": row["family_name"],
            }
        stats_by_member[member_id].append(row)

    # Build results
    results = []
    for member_id in seen_members:
        member_stats = stats_by_member[member_id]
        info = member_info[member_id]

        total_max = 0
        total_submitted = 0
        latest_submission = None
        by_content_type = []

        for stat in member_stats:
            ct_max = stat["max_assignments"]
            ct_submitted = stat["submitted_assignments"]
            ct_latest = stat["latest_submission_at"]

            total_max += ct_max
            total_submitted += ct_submitted
            if ct_latest and (latest_submission is None or ct_latest > latest_submission):
                latest_submission = ct_latest

            by_content_type.append({
                "course_content_type_id": stat["content_type_id"],
                "course_content_type_slug": stat["content_type_slug"],
                "course_content_type_title": stat["content_type_title"],
                "course_content_type_color": stat["content_type_color"],
                "max_assignments": ct_max,
                "submitted_assignments": ct_submitted,
                "progress_percentage": (ct_submitted / ct_max * 100) if ct_max > 0 else 0.0,
                "latest_submission_at": ct_latest,
            })

        results.append({
            "course_member_id": member_id,
            "user_id": info["user_id"],
            "username": info["username"],
            "given_name": info["given_name"],
            "family_name": info["family_name"],
            "total_max_assignments": total_max,
            "total_submitted_assignments": total_submitted,
            "overall_progress_percentage": (total_submitted / total_max * 100) if total_max > 0 else 0.0,
            "latest_submission_at": latest_submission,
            "by_content_type": by_content_type,
        })

    return results
