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

    def get_path_info(self, course_id: UUID | str) -> Dict[str, Dict[str, Any]]:
        """
        Get extended info for all course_content paths in a course.

        Includes title, course_content_kind_id, and submittable status.

        Args:
            course_id: The course ID

        Returns:
            Dict mapping path string to info dict with title, course_content_kind_id, submittable
        """
        results = (
            self.db.query(
                CourseContent.path,
                CourseContent.title,
                CourseContent.position,
                CourseContentKind.submittable,
                CourseContentType.color.label("course_content_type_color"),
            )
            .join(CourseContentType, CourseContentType.id == CourseContent.course_content_type_id)
            .join(CourseContentKind, CourseContentKind.id == CourseContentType.course_content_kind_id)
            .filter(
                CourseContent.course_id == course_id,
                CourseContent.archived_at.is_(None),
            )
            .all()
        )
        return {
            str(r.path): {
                "title": r.title,
                "submittable": r.submittable,
                "position": r.position,
                "course_content_type_color": r.course_content_type_color,
            }
            for r in results
        }

    def get_all_course_members_with_students_role(
        self,
        course_id: UUID | str,
    ) -> List[Dict[str, Any]]:
        """
        Get all course members with student role in a course.

        Args:
            course_id: The course ID

        Returns:
            List of dicts with course_member and user info including student_id
        """
        from computor_backend.model.auth import StudentProfile
        from computor_backend.model.course import Course

        # First get the organization_id for this course
        course = self.db.query(Course.organization_id).filter(Course.id == course_id).first()
        org_id = course.organization_id if course else None

        results = (
            self.db.query(
                CourseMember.id.label("course_member_id"),
                CourseMember.user_id.label("user_id"),
                User.username.label("username"),
                User.given_name.label("given_name"),
                User.family_name.label("family_name"),
                StudentProfile.student_id.label("student_id"),
            )
            .join(User, User.id == CourseMember.user_id)
            .outerjoin(
                StudentProfile,
                and_(
                    StudentProfile.user_id == CourseMember.user_id,
                    StudentProfile.organization_id == org_id,
                )
            )
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
                "student_id": r.student_id,
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

    def get_hierarchical_stats_for_member(
        self,
        course_member_id: UUID | str,
        course_id: UUID | str,
        path_prefix: Optional[str] = None,
        course_content_type_id: Optional[str] = None,
        max_depth: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get hierarchical grading statistics using database-level aggregation.

        Uses PostgreSQL ltree functions (nlevel, subpath) to calculate statistics
        at each path level in the database, avoiding Python-side iteration.

        Args:
            course_member_id: The course member ID
            course_id: The course ID
            path_prefix: Optional filter to specific subtree
            course_content_type_id: Optional filter by content type
            max_depth: Optional maximum depth for aggregation

        Returns:
            List of dicts with path-level aggregated statistics
        """
        # Build path prefix filter clause
        path_filter = ""
        if path_prefix:
            path_filter = "AND cc.path <@ :path_prefix::ltree"

        # Build content type filter clause
        content_type_filter = ""
        if course_content_type_id:
            content_type_filter = "AND cct.id = :course_content_type_id"

        # Build depth filter clause
        depth_filter = ""
        if max_depth:
            depth_filter = "AND path_depth <= :max_depth"

        # SQL query that uses PostgreSQL ltree functions for hierarchical aggregation
        # Extended to include grading statistics from submission_grade table
        sql = text(f"""
        WITH submittable_contents AS (
            -- Get all submittable course contents with their path levels
            SELECT
                cc.id as content_id,
                cc.path,
                cct.id as content_type_id,
                cct.slug as content_type_slug,
                cct.title as content_type_title,
                cct.color as content_type_color
            FROM course_content cc
            JOIN course_content_type cct ON cct.id = cc.course_content_type_id
            JOIN course_content_kind cck ON cck.id = cct.course_content_kind_id
            WHERE cc.course_id = :course_id
              AND cck.submittable = true
              AND cc.archived_at IS NULL
              {path_filter}
              {content_type_filter}
        ),
        submitted_contents AS (
            -- Get submitted contents for this member with latest submission info
            SELECT DISTINCT
                cc.id as content_id,
                MAX(sa.created_at) as latest_submission_at
            FROM submission_artifact sa
            JOIN submission_group sg ON sg.id = sa.submission_group_id
            JOIN submission_group_member sgm ON sgm.submission_group_id = sg.id
            JOIN course_content cc ON cc.id = sg.course_content_id
            JOIN course_content_type cct ON cct.id = cc.course_content_type_id
            JOIN course_content_kind cck ON cck.id = cct.course_content_kind_id
            WHERE sgm.course_member_id = :course_member_id
              AND cc.course_id = :course_id
              AND sa.submit = true
              AND cck.submittable = true
              AND cc.archived_at IS NULL
              {path_filter}
              {content_type_filter}
            GROUP BY cc.id
        ),
        graded_contents AS (
            -- Get grading info for ALL submittable contents (not just submitted)
            -- Unsubmitted = 0, ungraded submitted = 0, graded = actual grade
            -- Also fetch the latest grading status
            -- NOTE: Grades can be applied to any artifact, not just submitted ones
            SELECT
                sc.content_id,
                COALESCE(latest_grade.grade, 0) as grade,
                latest_grade.status as grading_status
            FROM submittable_contents sc
            LEFT JOIN LATERAL (
                SELECT sg.grade, sg.status
                FROM submission_grade sg
                JOIN submission_artifact sa ON sa.id = sg.artifact_id
                JOIN submission_group sgrp ON sgrp.id = sa.submission_group_id
                JOIN submission_group_member sgm ON sgm.submission_group_id = sgrp.id
                WHERE sgrp.course_content_id = sc.content_id
                  AND sgm.course_member_id = :course_member_id
                ORDER BY sg.graded_at DESC
                LIMIT 1
            ) latest_grade ON true
        ),
        path_levels AS (
            -- Generate all path prefixes at each level
            SELECT DISTINCT
                subpath(sc.path, 0, n) as path_prefix,
                n as path_depth
            FROM submittable_contents sc,
                 generate_series(1, nlevel(sc.path)) as n
            WHERE 1=1
              {depth_filter}
        ),
        aggregated AS (
            -- Aggregate statistics per path level and content type
            SELECT
                pl.path_prefix::text as path,
                pl.path_depth,
                sc.content_type_id,
                sc.content_type_slug,
                sc.content_type_title,
                sc.content_type_color,
                COUNT(sc.content_id) as max_assignments,
                COUNT(sub.content_id) as submitted_assignments,
                MAX(sub.latest_submission_at) as latest_submission_at,
                -- Grading statistics (unsubmitted and ungraded count as grade=0)
                -- graded_assignments = count of all submittable items (all have a grade: actual, or 0 if missing)
                COUNT(gc.content_id) as graded_assignments,
                -- average_grading = average including 0s for unsubmitted and ungraded items
                AVG(gc.grade) as average_grading,
                -- grading_status aggregation rules (returns string):
                -- 1. If ANY CORRECTION_NECESSARY(2) exists -> 'correction_necessary'
                -- 2. Else if ANY IMPROVEMENT_POSSIBLE(3) exists -> 'improvement_possible'
                -- 3. Else if ALL are CORRECTED(1) -> 'corrected'
                -- 4. Else -> 'not_reviewed' (mix of CORRECTED/NOT_REVIEWED, or all NOT_REVIEWED)
                CASE
                    WHEN MAX(CASE WHEN gc.grading_status = 2 THEN 1 ELSE 0 END) = 1 THEN 'correction_necessary'
                    WHEN MAX(CASE WHEN gc.grading_status = 3 THEN 1 ELSE 0 END) = 1 THEN 'improvement_possible'
                    WHEN MIN(COALESCE(gc.grading_status, 0)) = 1 AND MAX(COALESCE(gc.grading_status, 0)) = 1 THEN 'corrected'
                    ELSE 'not_reviewed'
                END as grading_status
            FROM path_levels pl
            JOIN submittable_contents sc ON sc.path <@ pl.path_prefix
            LEFT JOIN submitted_contents sub ON sub.content_id = sc.content_id
            JOIN graded_contents gc ON gc.content_id = sc.content_id
            GROUP BY pl.path_prefix, pl.path_depth, sc.content_type_id,
                     sc.content_type_slug, sc.content_type_title, sc.content_type_color
            ORDER BY pl.path_depth, pl.path_prefix::text, sc.content_type_slug
        )
        SELECT * FROM aggregated
        """)

        params = {
            "course_member_id": str(course_member_id),
            "course_id": str(course_id),
        }
        if path_prefix:
            params["path_prefix"] = path_prefix
        if course_content_type_id:
            params["course_content_type_id"] = str(course_content_type_id)
        if max_depth:
            params["max_depth"] = max_depth

        results = self.db.execute(sql, params).fetchall()

        return [
            {
                "path": r.path,
                "path_depth": r.path_depth,
                "content_type_id": str(r.content_type_id),
                "content_type_slug": r.content_type_slug,
                "content_type_title": r.content_type_title,
                "content_type_color": r.content_type_color,
                "max_assignments": r.max_assignments,
                "submitted_assignments": r.submitted_assignments,
                "latest_submission_at": r.latest_submission_at,
                # Grading statistics
                "graded_assignments": r.graded_assignments,
                "average_grading": float(r.average_grading) if r.average_grading is not None else None,
                "grading_status": r.grading_status,
            }
            for r in results
        ]

    def get_course_level_stats_for_all_members(
        self,
        course_id: UUID | str,
        path_prefix: Optional[str] = None,
        course_content_type_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get course-level grading statistics for ALL members using database aggregation.

        This is highly optimized - a single query calculates stats for all members.

        Args:
            course_id: The course ID
            path_prefix: Optional filter to specific subtree
            course_content_type_id: Optional filter by content type

        Returns:
            List of dicts with member info and their course-level statistics by content type
        """
        # Build path prefix filter clause
        path_filter = ""
        if path_prefix:
            path_filter = "AND cc.path <@ :path_prefix::ltree"

        # Build content type filter clause
        content_type_filter = ""
        if course_content_type_id:
            content_type_filter = "AND cct.id = :course_content_type_id"

        sql = text(f"""
        WITH course_org AS (
            -- Get the organization_id for this course
            SELECT organization_id FROM course WHERE id = :course_id
        ),
        submittable_contents AS (
            -- Get all submittable course contents
            SELECT
                cc.id as content_id,
                cc.path,
                cct.id as content_type_id,
                cct.slug as content_type_slug,
                cct.title as content_type_title,
                cct.color as content_type_color
            FROM course_content cc
            JOIN course_content_type cct ON cct.id = cc.course_content_type_id
            JOIN course_content_kind cck ON cck.id = cct.course_content_kind_id
            WHERE cc.course_id = :course_id
              AND cck.submittable = true
              AND cc.archived_at IS NULL
              {path_filter}
              {content_type_filter}
        ),
        content_type_counts AS (
            -- Pre-calculate max counts per content type
            SELECT
                content_type_id,
                content_type_slug,
                content_type_title,
                content_type_color,
                COUNT(*) as max_assignments
            FROM submittable_contents
            GROUP BY content_type_id, content_type_slug, content_type_title, content_type_color
        ),
        all_students AS (
            -- Get all students in the course with student_id from student_profile
            SELECT
                cm.id as course_member_id,
                cm.user_id,
                u.username,
                u.given_name,
                u.family_name,
                sp.student_id
            FROM course_member cm
            JOIN "user" u ON u.id = cm.user_id
            LEFT JOIN student_profile sp ON sp.user_id = cm.user_id
                AND sp.organization_id = (SELECT organization_id FROM course_org)
            WHERE cm.course_id = :course_id
              AND cm.course_role_id = '_student'
            ORDER BY u.family_name, u.given_name
        ),
        submitted_by_member_and_type AS (
            -- Get submitted counts per member and content type
            SELECT
                sgm.course_member_id,
                cct.id as content_type_id,
                COUNT(DISTINCT cc.id) as submitted_assignments,
                MAX(sa.created_at) as latest_submission_at
            FROM submission_artifact sa
            JOIN submission_group sg ON sg.id = sa.submission_group_id
            JOIN submission_group_member sgm ON sgm.submission_group_id = sg.id
            JOIN course_content cc ON cc.id = sg.course_content_id
            JOIN course_content_type cct ON cct.id = cc.course_content_type_id
            JOIN course_content_kind cck ON cck.id = cct.course_content_kind_id
            WHERE cc.course_id = :course_id
              AND sa.submit = true
              AND cck.submittable = true
              AND cc.archived_at IS NULL
              {path_filter}
              {content_type_filter}
            GROUP BY sgm.course_member_id, cct.id
        ),
        all_contents_with_grades AS (
            -- For each submittable content per member, get latest grade (or 0 if unsubmitted/ungraded)
            -- This ensures ALL submittable contents are included in the average
            SELECT
                s.course_member_id,
                sc.content_id,
                sc.content_type_id,
                COALESCE(latest_grade.grade, 0) as grade
            FROM all_students s
            CROSS JOIN submittable_contents sc
            LEFT JOIN LATERAL (
                SELECT sg.grade
                FROM submission_grade sg
                JOIN submission_artifact sa ON sa.id = sg.artifact_id
                JOIN submission_group sgrp ON sgrp.id = sa.submission_group_id
                JOIN submission_group_member sgm ON sgm.submission_group_id = sgrp.id
                WHERE sgrp.course_content_id = sc.content_id
                  AND sgm.course_member_id = s.course_member_id
                  AND sa.submit = true
                ORDER BY sg.graded_at DESC
                LIMIT 1
            ) latest_grade ON true
        ),
        graded_by_member_and_type AS (
            -- Aggregate grading stats per member and content type
            -- All submittable contents included (unsubmitted/ungraded = 0)
            SELECT
                course_member_id,
                content_type_id,
                COUNT(*) as graded_assignments,
                AVG(grade) as average_grading
            FROM all_contents_with_grades
            GROUP BY course_member_id, content_type_id
        )
        SELECT
            s.course_member_id,
            s.user_id,
            s.username,
            s.given_name,
            s.family_name,
            s.student_id,
            ctc.content_type_id,
            ctc.content_type_slug,
            ctc.content_type_title,
            ctc.content_type_color,
            ctc.max_assignments,
            COALESCE(sbmt.submitted_assignments, 0) as submitted_assignments,
            sbmt.latest_submission_at,
            COALESCE(grd.graded_assignments, 0) as graded_assignments,
            grd.average_grading
        FROM all_students s
        CROSS JOIN content_type_counts ctc
        LEFT JOIN submitted_by_member_and_type sbmt
            ON sbmt.course_member_id = s.course_member_id
            AND sbmt.content_type_id = ctc.content_type_id
        LEFT JOIN graded_by_member_and_type grd
            ON grd.course_member_id = s.course_member_id
            AND grd.content_type_id = ctc.content_type_id
        ORDER BY s.family_name, s.given_name, ctc.content_type_slug
        """)

        params = {"course_id": str(course_id)}
        if path_prefix:
            params["path_prefix"] = path_prefix
        if course_content_type_id:
            params["course_content_type_id"] = str(course_content_type_id)

        results = self.db.execute(sql, params).fetchall()

        return [
            {
                "course_member_id": str(r.course_member_id),
                "user_id": str(r.user_id) if r.user_id else None,
                "username": r.username,
                "given_name": r.given_name,
                "family_name": r.family_name,
                "student_id": r.student_id,
                "content_type_id": str(r.content_type_id),
                "content_type_slug": r.content_type_slug,
                "content_type_title": r.content_type_title,
                "content_type_color": r.content_type_color,
                "max_assignments": r.max_assignments,
                "submitted_assignments": r.submitted_assignments,
                "latest_submission_at": r.latest_submission_at,
                # Grading statistics
                "graded_assignments": r.graded_assignments,
                "average_grading": float(r.average_grading) if r.average_grading is not None else None,
            }
            for r in results
        ]

    def get_grading_for_assignment(
        self,
        course_member_id: UUID | str,
        course_content_id: UUID | str,
    ) -> Optional[float]:
        """
        Get the latest grade for a specific assignment for a course member.

        Args:
            course_member_id: The course member ID
            course_content_id: The course content ID (assignment)

        Returns:
            The grade (0.0-1.0) or None if not graded
        """
        sql = text("""
        SELECT sg.grade
        FROM submission_grade sg
        JOIN submission_artifact sa ON sa.id = sg.artifact_id
        JOIN submission_group sgrp ON sgrp.id = sa.submission_group_id
        JOIN submission_group_member sgm ON sgm.submission_group_id = sgrp.id
        WHERE sgm.course_member_id = :course_member_id
          AND sgrp.course_content_id = :course_content_id
          AND sa.submit = true
        ORDER BY sg.graded_at DESC
        LIMIT 1
        """)

        result = self.db.execute(sql, {
            "course_member_id": str(course_member_id),
            "course_content_id": str(course_content_id),
        }).fetchone()

        return float(result.grade) if result else None

    def get_assignment_details_for_member(
        self,
        course_member_id: UUID | str,
        course_id: UUID | str,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get per-assignment details for a course member including:
        - Latest result info (id, grade, status, created_at)
        - Test runs count and max_test_runs limit
        - Submissions count and max_submissions limit

        Args:
            course_member_id: The course member ID
            course_id: The course ID

        Returns:
            Dict mapping course_content path to assignment details
        """
        sql = text("""
        WITH member_submission_groups AS (
            -- Get all submission groups this member belongs to
            SELECT DISTINCT
                sg.id as submission_group_id,
                sg.course_content_id,
                sg.max_test_runs as sg_max_test_runs,
                sg.max_submissions as sg_max_submissions
            FROM submission_group sg
            JOIN submission_group_member sgm ON sgm.submission_group_id = sg.id
            WHERE sgm.course_member_id = :course_member_id
              AND sg.course_id = :course_id
        ),
        submittable_contents AS (
            -- Get all submittable course contents
            SELECT
                cc.id as content_id,
                cc.path,
                cc.max_test_runs as cc_max_test_runs,
                cc.max_submissions as cc_max_submissions
            FROM course_content cc
            JOIN course_content_type cct ON cct.id = cc.course_content_type_id
            JOIN course_content_kind cck ON cck.id = cct.course_content_kind_id
            WHERE cc.course_id = :course_id
              AND cck.submittable = true
              AND cc.archived_at IS NULL
        ),
        latest_results AS (
            -- Get the latest result for each content
            SELECT DISTINCT ON (sc.content_id)
                sc.content_id,
                r.id as result_id,
                r.result as result_grade,
                r.status as result_status,
                r.created_at as result_created_at
            FROM submittable_contents sc
            JOIN member_submission_groups msg ON msg.course_content_id = sc.content_id
            LEFT JOIN result r ON r.course_content_id = sc.content_id
                AND r.course_member_id = :course_member_id
            ORDER BY sc.content_id, r.created_at DESC NULLS LAST
        ),
        test_runs_counts AS (
            -- Count test runs (all results, not just submitted)
            SELECT
                sc.content_id,
                COUNT(r.id) as test_runs_count
            FROM submittable_contents sc
            LEFT JOIN result r ON r.course_content_id = sc.content_id
                AND r.course_member_id = :course_member_id
            GROUP BY sc.content_id
        ),
        submissions_counts AS (
            -- Count submissions (artifacts with submit=true)
            SELECT
                sc.content_id,
                COUNT(DISTINCT sa.id) as submissions_count
            FROM submittable_contents sc
            JOIN member_submission_groups msg ON msg.course_content_id = sc.content_id
            LEFT JOIN submission_artifact sa ON sa.submission_group_id = msg.submission_group_id
                AND sa.submit = true
            GROUP BY sc.content_id
        )
        SELECT
            sc.path::text as path,
            sc.content_id,
            -- Limits: prefer submission_group override, fallback to course_content
            COALESCE(msg.sg_max_test_runs, sc.cc_max_test_runs) as max_test_runs,
            COALESCE(msg.sg_max_submissions, sc.cc_max_submissions) as max_submissions,
            -- Latest result info
            lr.result_id,
            lr.result_grade,
            lr.result_status,
            lr.result_created_at,
            -- Counts
            COALESCE(trc.test_runs_count, 0) as test_runs_count,
            COALESCE(smc.submissions_count, 0) as submissions_count
        FROM submittable_contents sc
        LEFT JOIN member_submission_groups msg ON msg.course_content_id = sc.content_id
        LEFT JOIN latest_results lr ON lr.content_id = sc.content_id
        LEFT JOIN test_runs_counts trc ON trc.content_id = sc.content_id
        LEFT JOIN submissions_counts smc ON smc.content_id = sc.content_id
        """)

        results = self.db.execute(sql, {
            "course_member_id": str(course_member_id),
            "course_id": str(course_id),
        }).fetchall()

        return {
            r.path: {
                "content_id": str(r.content_id),
                "max_test_runs": r.max_test_runs,
                "max_submissions": r.max_submissions,
                "latest_result_id": str(r.result_id) if r.result_id else None,
                "latest_result_grade": float(r.result_grade) if r.result_grade is not None else None,
                "latest_result_status": r.result_status,
                "latest_result_created_at": r.result_created_at,
                "test_runs_count": r.test_runs_count,
                "submissions_count": r.submissions_count,
            }
            for r in results
        }


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
