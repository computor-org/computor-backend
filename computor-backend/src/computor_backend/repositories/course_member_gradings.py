"""
Repository for course member grading statistics.

This module provides optimized queries for calculating aggregated progress
statistics for course members, including hierarchical aggregation by ltree path
and breakdown by course content type.
"""

import logging
from typing import Optional, Dict, List, Any
from uuid import UUID
from datetime import datetime

from sqlalchemy import func, and_, text, case, literal
from sqlalchemy.orm import Session

from computor_backend.model.course import (
    CourseContent,
    CourseContentKind,
    CourseContentType,
    CourseMember,
    CourseRole,
    SubmissionGroup,
    SubmissionGroupMember,
)
from computor_backend.model.artifact import SubmissionArtifact
from computor_backend.model.auth import User
from computor_backend.custom_types import Ltree

logger = logging.getLogger(__name__)


class CourseMemberGradingsRepository:
    """Repository for course member grading statistics."""

    def __init__(self, db: Session):
        self.db = db

    def get_submittable_contents(
        self,
        course_id: UUID | str,
        path_prefix: Optional[str] = None,
        course_content_type_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all submittable course_contents for a course.

        Args:
            course_id: The course ID
            path_prefix: Optional filter to specific subtree
            course_content_type_id: Optional filter by content type

        Returns:
            List of dicts with course_content info
        """
        query = (
            self.db.query(
                CourseContent.id.label("course_content_id"),
                CourseContent.path.label("path"),
                CourseContent.title.label("title"),
                CourseContentType.id.label("course_content_type_id"),
                CourseContentType.slug.label("course_content_type_slug"),
                CourseContentType.title.label("course_content_type_title"),
                CourseContentType.color.label("course_content_type_color"),
            )
            .join(CourseContentType, CourseContentType.id == CourseContent.course_content_type_id)
            .join(CourseContentKind, CourseContentKind.id == CourseContentType.course_content_kind_id)
            .filter(
                CourseContent.course_id == course_id,
                CourseContentKind.submittable == True,
                CourseContent.archived_at.is_(None),
            )
        )

        if path_prefix:
            # Filter by path prefix using ltree descendant operator
            query = query.filter(
                text("course_content.path <@ :path_prefix::ltree OR course_content.path::text = :path_prefix_str")
            ).params(path_prefix=path_prefix, path_prefix_str=path_prefix)

        if course_content_type_id:
            query = query.filter(CourseContentType.id == course_content_type_id)

        results = query.all()
        return [
            {
                "course_content_id": str(r.course_content_id),
                "path": str(r.path),
                "title": r.title,
                "course_content_type_id": str(r.course_content_type_id),
                "course_content_type_slug": r.course_content_type_slug,
                "course_content_type_title": r.course_content_type_title,
                "course_content_type_color": r.course_content_type_color,
            }
            for r in results
        ]

    def get_submitted_contents(
        self,
        course_member_id: UUID | str,
        course_id: UUID | str,
        path_prefix: Optional[str] = None,
        course_content_type_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get course_contents that have at least one submitted artifact for this member.

        Args:
            course_member_id: The course member ID
            course_id: The course ID
            path_prefix: Optional filter to specific subtree
            course_content_type_id: Optional filter by content type

        Returns:
            List of dicts with submitted content info including latest submission date
        """
        query = (
            self.db.query(
                CourseContent.id.label("course_content_id"),
                CourseContent.path.label("path"),
                CourseContentType.id.label("course_content_type_id"),
                CourseContentType.slug.label("course_content_type_slug"),
                func.max(SubmissionArtifact.created_at).label("latest_submission_at"),
            )
            .select_from(SubmissionArtifact)
            .join(SubmissionGroup, SubmissionGroup.id == SubmissionArtifact.submission_group_id)
            .join(SubmissionGroupMember, SubmissionGroupMember.submission_group_id == SubmissionGroup.id)
            .join(CourseContent, CourseContent.id == SubmissionGroup.course_content_id)
            .join(CourseContentType, CourseContentType.id == CourseContent.course_content_type_id)
            .join(CourseContentKind, CourseContentKind.id == CourseContentType.course_content_kind_id)
            .filter(
                SubmissionGroupMember.course_member_id == course_member_id,
                CourseContent.course_id == course_id,
                SubmissionArtifact.submit == True,
                CourseContentKind.submittable == True,
                CourseContent.archived_at.is_(None),
            )
            .group_by(
                CourseContent.id,
                CourseContent.path,
                CourseContentType.id,
                CourseContentType.slug,
            )
        )

        if path_prefix:
            query = query.filter(
                text("course_content.path <@ :path_prefix::ltree OR course_content.path::text = :path_prefix_str")
            ).params(path_prefix=path_prefix, path_prefix_str=path_prefix)

        if course_content_type_id:
            query = query.filter(CourseContentType.id == course_content_type_id)

        results = query.all()
        return [
            {
                "course_content_id": str(r.course_content_id),
                "path": str(r.path),
                "course_content_type_id": str(r.course_content_type_id),
                "course_content_type_slug": r.course_content_type_slug,
                "latest_submission_at": r.latest_submission_at,
            }
            for r in results
        ]

    def get_path_titles(self, course_id: UUID | str) -> Dict[str, str]:
        """
        Get titles for all course_content paths in a course.

        Args:
            course_id: The course ID

        Returns:
            Dict mapping path string to title
        """
        results = (
            self.db.query(CourseContent.path, CourseContent.title)
            .filter(
                CourseContent.course_id == course_id,
                CourseContent.archived_at.is_(None),
            )
            .all()
        )
        return {str(r.path): r.title for r in results}

    def get_all_course_members_with_students_role(
        self,
        course_id: UUID | str,
    ) -> List[Dict[str, Any]]:
        """
        Get all course members with student role in a course.

        Args:
            course_id: The course ID

        Returns:
            List of dicts with course_member and user info
        """
        results = (
            self.db.query(
                CourseMember.id.label("course_member_id"),
                CourseMember.user_id.label("user_id"),
                User.username.label("username"),
                User.given_name.label("given_name"),
                User.family_name.label("family_name"),
            )
            .join(User, User.id == CourseMember.user_id)
            .filter(
                CourseMember.course_id == course_id,
                CourseMember.course_role_id == "_student",
            )
            .order_by(User.family_name, User.given_name)
            .all()
        )
        return [
            {
                "course_member_id": str(r.course_member_id),
                "user_id": str(r.user_id) if r.user_id else None,
                "username": r.username,
                "given_name": r.given_name,
                "family_name": r.family_name,
            }
            for r in results
        ]

    def get_all_submitted_contents_for_course(
        self,
        course_id: UUID | str,
        path_prefix: Optional[str] = None,
        course_content_type_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all submitted contents for ALL course members in a course.

        This is an optimized batch query that gets submission data for all
        members at once, avoiding N+1 queries.

        Args:
            course_id: The course ID
            path_prefix: Optional filter to specific subtree
            course_content_type_id: Optional filter by content type

        Returns:
            List of dicts with course_member_id, course_content_id, and latest_submission_at
        """
        query = (
            self.db.query(
                SubmissionGroupMember.course_member_id.label("course_member_id"),
                CourseContent.id.label("course_content_id"),
                CourseContent.path.label("path"),
                CourseContentType.id.label("course_content_type_id"),
                CourseContentType.slug.label("course_content_type_slug"),
                func.max(SubmissionArtifact.created_at).label("latest_submission_at"),
            )
            .select_from(SubmissionArtifact)
            .join(SubmissionGroup, SubmissionGroup.id == SubmissionArtifact.submission_group_id)
            .join(SubmissionGroupMember, SubmissionGroupMember.submission_group_id == SubmissionGroup.id)
            .join(CourseContent, CourseContent.id == SubmissionGroup.course_content_id)
            .join(CourseContentType, CourseContentType.id == CourseContent.course_content_type_id)
            .join(CourseContentKind, CourseContentKind.id == CourseContentType.course_content_kind_id)
            .filter(
                CourseContent.course_id == course_id,
                SubmissionArtifact.submit == True,
                CourseContentKind.submittable == True,
                CourseContent.archived_at.is_(None),
            )
            .group_by(
                SubmissionGroupMember.course_member_id,
                CourseContent.id,
                CourseContent.path,
                CourseContentType.id,
                CourseContentType.slug,
            )
        )

        if path_prefix:
            query = query.filter(
                text("course_content.path <@ :path_prefix::ltree OR course_content.path::text = :path_prefix_str")
            ).params(path_prefix=path_prefix, path_prefix_str=path_prefix)

        if course_content_type_id:
            query = query.filter(CourseContentType.id == course_content_type_id)

        results = query.all()
        return [
            {
                "course_member_id": str(r.course_member_id),
                "course_content_id": str(r.course_content_id),
                "path": str(r.path),
                "course_content_type_id": str(r.course_content_type_id),
                "course_content_type_slug": r.course_content_type_slug,
                "latest_submission_at": r.latest_submission_at,
            }
            for r in results
        ]


def calculate_grading_stats(
    submittable_contents: List[Dict[str, Any]],
    submitted_contents: List[Dict[str, Any]],
    path_titles: Dict[str, str],
    max_depth: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Calculate hierarchical grading statistics from raw content data.

    This is a pure function that aggregates the data from the repository queries.
    Uses Ltree for path operations.

    Args:
        submittable_contents: List of all submittable course_contents
        submitted_contents: List of submitted course_contents with latest_submission_at
        path_titles: Dict mapping path to title
        max_depth: Optional maximum depth for aggregation

    Returns:
        Dict with aggregated statistics ready for DTO conversion
    """
    # Build sets for quick lookup
    submitted_content_ids = {c["course_content_id"] for c in submitted_contents}

    # Build submitted content info by id for latest_submission_at lookup
    submitted_info_by_id = {c["course_content_id"]: c for c in submitted_contents}

    # Get all unique content types
    content_types = {}
    for content in submittable_contents:
        ct_id = content["course_content_type_id"]
        if ct_id not in content_types:
            content_types[ct_id] = {
                "course_content_type_id": ct_id,
                "course_content_type_slug": content["course_content_type_slug"],
                "course_content_type_title": content["course_content_type_title"],
                "course_content_type_color": content["course_content_type_color"],
            }

    # Get all unique path prefixes at all levels using Ltree
    all_paths = set()
    for content in submittable_contents:
        ltree_path = Ltree(content["path"])
        segments = ltree_path.path.split(".")
        for i in range(1, len(segments) + 1):
            prefix = ".".join(segments[:i])
            all_paths.add(prefix)

    # Calculate depth and filter if needed
    # Depth is number of segments (nlevel in PostgreSQL)
    if max_depth is not None:
        all_paths = {p for p in all_paths if len(p.split(".")) <= max_depth}

    # Sort paths by depth then alphabetically
    sorted_paths = sorted(all_paths, key=lambda p: (len(p.split(".")), p))

    # Build aggregation for each path level
    nodes = []
    for path_str in sorted_paths:
        path_ltree = Ltree(path_str)

        # Find all submittable contents at or under this path using Ltree.descendant_of
        # Note: descendant_of returns True for same path and all child paths
        contents_under_path = [
            c for c in submittable_contents
            if Ltree(c["path"]).descendant_of(path_ltree)
        ]

        if not contents_under_path:
            continue

        # Calculate overall stats for this path
        max_assignments = len(contents_under_path)
        submitted_assignments = sum(
            1 for c in contents_under_path
            if c["course_content_id"] in submitted_content_ids
        )

        # Find latest submission under this path
        latest_submission_at = None
        for c in contents_under_path:
            if c["course_content_id"] in submitted_info_by_id:
                sub_info = submitted_info_by_id[c["course_content_id"]]
                sub_date = sub_info["latest_submission_at"]
                if sub_date and (latest_submission_at is None or sub_date > latest_submission_at):
                    latest_submission_at = sub_date

        # Calculate by content type
        by_content_type = []
        for ct_id, ct_info in content_types.items():
            ct_contents = [c for c in contents_under_path if c["course_content_type_id"] == ct_id]
            if not ct_contents:
                continue

            ct_max = len(ct_contents)
            ct_submitted = sum(
                1 for c in ct_contents
                if c["course_content_id"] in submitted_content_ids
            )

            # Latest submission for this content type
            ct_latest = None
            for c in ct_contents:
                if c["course_content_id"] in submitted_info_by_id:
                    sub_info = submitted_info_by_id[c["course_content_id"]]
                    sub_date = sub_info["latest_submission_at"]
                    if sub_date and (ct_latest is None or sub_date > ct_latest):
                        ct_latest = sub_date

            by_content_type.append({
                **ct_info,
                "max_assignments": ct_max,
                "submitted_assignments": ct_submitted,
                "progress_percentage": (ct_submitted / ct_max * 100) if ct_max > 0 else 0.0,
                "latest_submission_at": ct_latest,
            })

        nodes.append({
            "path": path_str,
            "title": path_titles.get(path_str),
            "max_assignments": max_assignments,
            "submitted_assignments": submitted_assignments,
            "progress_percentage": (submitted_assignments / max_assignments * 100) if max_assignments > 0 else 0.0,
            "latest_submission_at": latest_submission_at,
            "by_content_type": by_content_type,
        })

    # Calculate overall totals (course level)
    total_max = len(submittable_contents)
    total_submitted = len(submitted_content_ids & {c["course_content_id"] for c in submittable_contents})

    # Overall latest submission
    overall_latest = None
    for c in submitted_contents:
        sub_date = c["latest_submission_at"]
        if sub_date and (overall_latest is None or sub_date > overall_latest):
            overall_latest = sub_date

    # Overall by content type
    overall_by_content_type = []
    for ct_id, ct_info in content_types.items():
        ct_contents = [c for c in submittable_contents if c["course_content_type_id"] == ct_id]
        if not ct_contents:
            continue

        ct_max = len(ct_contents)
        ct_submitted = sum(
            1 for c in ct_contents
            if c["course_content_id"] in submitted_content_ids
        )

        # Latest submission for this content type at course level
        ct_latest = None
        for c in ct_contents:
            if c["course_content_id"] in submitted_info_by_id:
                sub_info = submitted_info_by_id[c["course_content_id"]]
                sub_date = sub_info["latest_submission_at"]
                if sub_date and (ct_latest is None or sub_date > ct_latest):
                    ct_latest = sub_date

        overall_by_content_type.append({
            **ct_info,
            "max_assignments": ct_max,
            "submitted_assignments": ct_submitted,
            "progress_percentage": (ct_submitted / ct_max * 100) if ct_max > 0 else 0.0,
            "latest_submission_at": ct_latest,
        })

    return {
        "total_max_assignments": total_max,
        "total_submitted_assignments": total_submitted,
        "overall_progress_percentage": (total_submitted / total_max * 100) if total_max > 0 else 0.0,
        "latest_submission_at": overall_latest,
        "by_content_type": overall_by_content_type,
        "nodes": nodes,
    }


def calculate_grading_stats_for_all_members(
    submittable_contents: List[Dict[str, Any]],
    all_submitted_contents: List[Dict[str, Any]],
    course_members: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Calculate grading statistics for all course members at once.

    This is an optimized batch calculation that processes all members in one pass.
    Returns only course-level totals (no hierarchical nodes) for efficiency.

    Args:
        submittable_contents: List of all submittable course_contents in the course
        all_submitted_contents: List of all submitted contents for all members
        course_members: List of course members with user info

    Returns:
        List of dicts with grading stats per course member
    """
    # Get all unique content types from submittable contents
    content_types = {}
    for content in submittable_contents:
        ct_id = content["course_content_type_id"]
        if ct_id not in content_types:
            content_types[ct_id] = {
                "course_content_type_id": ct_id,
                "course_content_type_slug": content["course_content_type_slug"],
                "course_content_type_title": content["course_content_type_title"],
                "course_content_type_color": content["course_content_type_color"],
            }

    # Total max assignments (same for all members)
    total_max = len(submittable_contents)

    # Group submitted contents by course_member_id
    submitted_by_member: Dict[str, List[Dict[str, Any]]] = {}
    for sub in all_submitted_contents:
        member_id = sub["course_member_id"]
        if member_id not in submitted_by_member:
            submitted_by_member[member_id] = []
        submitted_by_member[member_id].append(sub)

    # Calculate stats per member
    results = []
    for member in course_members:
        member_id = member["course_member_id"]
        member_submissions = submitted_by_member.get(member_id, [])

        # Build set of submitted content IDs for this member
        submitted_content_ids = {s["course_content_id"] for s in member_submissions}

        # Count submitted assignments
        total_submitted = len(submitted_content_ids & {c["course_content_id"] for c in submittable_contents})

        # Find latest submission
        latest_submission_at = None
        for sub in member_submissions:
            sub_date = sub["latest_submission_at"]
            if sub_date and (latest_submission_at is None or sub_date > latest_submission_at):
                latest_submission_at = sub_date

        # Calculate by content type
        by_content_type = []
        for ct_id, ct_info in content_types.items():
            ct_contents = [c for c in submittable_contents if c["course_content_type_id"] == ct_id]
            if not ct_contents:
                continue

            ct_max = len(ct_contents)
            ct_content_ids = {c["course_content_id"] for c in ct_contents}
            ct_submitted = len(submitted_content_ids & ct_content_ids)

            # Latest submission for this content type
            ct_latest = None
            for sub in member_submissions:
                if sub["course_content_id"] in ct_content_ids:
                    sub_date = sub["latest_submission_at"]
                    if sub_date and (ct_latest is None or sub_date > ct_latest):
                        ct_latest = sub_date

            by_content_type.append({
                **ct_info,
                "max_assignments": ct_max,
                "submitted_assignments": ct_submitted,
                "progress_percentage": (ct_submitted / ct_max * 100) if ct_max > 0 else 0.0,
                "latest_submission_at": ct_latest,
            })

        results.append({
            "course_member_id": member_id,
            "user_id": member.get("user_id"),
            "username": member.get("username"),
            "given_name": member.get("given_name"),
            "family_name": member.get("family_name"),
            "total_max_assignments": total_max,
            "total_submitted_assignments": total_submitted,
            "overall_progress_percentage": (total_submitted / total_max * 100) if total_max > 0 else 0.0,
            "latest_submission_at": latest_submission_at,
            "by_content_type": by_content_type,
        })

    return results
