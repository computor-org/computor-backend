"""
Course member gradings view repository with caching.

This repository handles complex grading statistics queries for course members,
providing aggregated progress data with hierarchical breakdowns.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
import logging

from .view_base import ViewRepository
from .course_member_gradings import CourseMemberGradingsRepository
from ..model.course import Course, CourseMember
from ..permissions.principal import Principal
from ..permissions.core import check_course_permissions
from ..api.exceptions import NotFoundException, ForbiddenException
from computor_types.course_member_gradings import (
    CourseMemberGradingsGet,
    CourseMemberGradingsList,
    CourseMemberGradingsQuery,
    CourseMemberGradingNode,
    ContentTypeGradingStats,
)

logger = logging.getLogger(__name__)


class CourseMemberGradingsViewRepository(ViewRepository):
    """
    Repository for course member grading statistics views with caching.

    Handles:
    - Individual student grading stats (full hierarchy)
    - Course-wide grading stats (all students)
    - Automatic cache invalidation via tags
    """

    def get_default_ttl(self) -> int:
        """Grading stats cached for 30 minutes (dashboard-style caching)."""
        return 1800  # 30 minutes

    async def get_course_member_gradings(
        self,
        course_member_id: UUID | str,
        permissions: Principal,
        params: CourseMemberGradingsQuery,
    ) -> CourseMemberGradingsGet:
        """
        Get grading statistics for a specific course member.

        This method:
        1. Checks cache first (no DB connection needed on cache hit)
        2. Validates permissions
        3. Calculates full hierarchy stats
        4. Caches result with proper tags

        Args:
            course_member_id: Course member ID
            permissions: Current user permissions
            params: Query parameters (course_id)

        Returns:
            CourseMemberGradingsGet with full hierarchy

        Raises:
            NotFoundException: If course member not found
            ForbiddenException: If user lacks permissions
        """
        user_id = permissions.get_user_id()

        # Try cache FIRST (before any DB access)
        cache_key = f"cm_grading:{course_member_id}"
        cached = self._get_cached_view(
            user_id=str(user_id),
            view_type=cache_key
        )

        if cached is not None:
            return CourseMemberGradingsGet(**cached)

        # Cache miss - now access database (lazy connection)
        from computor_backend.model.auth import User, StudentProfile
        from sqlalchemy import and_

        course_member = self.db.query(CourseMember).filter(
            CourseMember.id == course_member_id
        ).first()

        if course_member is None:
            raise NotFoundException(detail=f"Course member {course_member_id} not found")

        # Determine course_id
        course_id = params.course_id or str(course_member.course_id)

        # Check if course_id matches the member's course
        if str(course_member.course_id) != course_id:
            raise NotFoundException(
                detail=f"Course member {course_member_id} does not belong to course {course_id}"
            )

        # Get organization_id from course for student_profile lookup
        course = self.db.query(Course).filter(Course.id == course_id).first()
        org_id = course.organization_id if course else None

        # Fetch user info and student_id
        member_info = (
            self.db.query(
                User.id.label("user_id"),
                User.username,
                User.given_name,
                User.family_name,
                StudentProfile.student_id,
            )
            .select_from(User)
            .outerjoin(
                StudentProfile,
                and_(
                    StudentProfile.user_id == User.id,
                    StudentProfile.organization_id == org_id,
                )
            )
            .filter(User.id == course_member.user_id)
            .first()
        )

        # Permission check: Tutor or higher role required
        has_course_perms = check_course_permissions(
            permissions, CourseMember, "_tutor", self.db
        ).filter(
            CourseMember.course_id == course_id,
            CourseMember.user_id == user_id
        ).first()

        if not has_course_perms:
            raise ForbiddenException(
                detail="You don't have permission to view this course member's grading statistics. "
                       "Tutor role or higher is required."
            )

        # Initialize data repository
        data_repo = CourseMemberGradingsRepository(self.db)

        # Get hierarchical stats using database-level aggregation (full hierarchy always)
        db_stats = data_repo.get_hierarchical_stats_for_member(
            course_member_id=course_member_id,
            course_id=course_id,
            path_prefix=None,  # Always full hierarchy
            course_content_type_id=None,  # All content types
            max_depth=None,  # All depths
        )

        # Get path info for display (includes title, course_content_kind_id, submittable)
        path_info = data_repo.get_path_info(course_id)

        # Get per-assignment details (latest result, test runs/submissions counts)
        assignment_details = data_repo.get_assignment_details_for_member(
            course_member_id=course_member_id,
            course_id=course_id,
        )

        # Process database results into the expected structure
        stats = self._process_hierarchical_stats(db_stats, path_info, assignment_details)

        # Convert to DTOs
        by_content_type = [
            ContentTypeGradingStats(**ct_stats)
            for ct_stats in stats["by_content_type"]
        ]

        nodes = [
            CourseMemberGradingNode(
                path=node["path"],
                title=node["title"],
                submittable=node["submittable"],
                position=node["position"],
                course_content_type_color=node["course_content_type_color"],
                max_assignments=node["max_assignments"],
                submitted_assignments=node["submitted_assignments"],
                progress_percentage=node["progress_percentage"],
                latest_submission_at=node["latest_submission_at"],
                by_content_type=[
                    ContentTypeGradingStats(**ct)
                    for ct in node["by_content_type"]
                ],
                grading=node["grading"],
                average_grading=node["average_grading"],
                graded_assignments=node["graded_assignments"],
                status=node["status"],
                # Per-assignment details (only for submittable nodes)
                latest_result_id=node.get("latest_result_id"),
                latest_result_grade=node.get("latest_result_grade"),
                latest_result_status=node.get("latest_result_status"),
                latest_result_created_at=node.get("latest_result_created_at"),
                test_runs_count=node.get("test_runs_count"),
                max_test_runs=node.get("max_test_runs"),
                submissions_count=node.get("submissions_count"),
                max_submissions=node.get("max_submissions"),
                graded_by_course_member=node.get("graded_by_course_member"),
            )
            for node in stats["nodes"]
        ]

        result = CourseMemberGradingsGet(
            course_member_id=str(course_member_id),
            course_id=course_id,
            user_id=str(member_info.user_id) if member_info and member_info.user_id else None,
            username=member_info.username if member_info else None,
            given_name=member_info.given_name if member_info else None,
            family_name=member_info.family_name if member_info else None,
            student_id=member_info.student_id if member_info else None,
            total_max_assignments=stats["total_max_assignments"],
            total_submitted_assignments=stats["total_submitted_assignments"],
            overall_progress_percentage=stats["overall_progress_percentage"],
            latest_submission_at=stats["latest_submission_at"],
            overall_average_grading=stats["overall_average_grading"],
            by_content_type=by_content_type,
            nodes=nodes,
        )

        # Cache the result with tags for invalidation
        self._set_cached_view(
            user_id=str(user_id),
            view_type=cache_key,
            data=result.model_dump(),
            related_ids={
                'course_member_id': str(course_member_id),
                'course_id': str(course_id),
                'cm_grading': str(course_member_id),  # Primary tag for invalidation
            }
        )

        return result

    async def list_course_member_gradings(
        self,
        course_id: UUID | str,
        permissions: Principal,
        params: CourseMemberGradingsQuery,
    ) -> List[CourseMemberGradingsList]:
        """
        Get grading statistics for all course members in a course.

        This method leverages per-student caching for efficiency.

        Args:
            course_id: Course ID
            permissions: Current user permissions
            params: Query parameters

        Returns:
            List of CourseMemberGradingsList

        Raises:
            NotFoundException: If course not found
            ForbiddenException: If user lacks permissions
        """
        # Verify course exists (need DB for this)
        course = self.db.query(Course).filter(Course.id == course_id).first()
        if course is None:
            raise NotFoundException(detail=f"Course {course_id} not found")

        # Permission check: Tutor or higher role required
        user_id = permissions.get_user_id()
        has_course_perms = check_course_permissions(
            permissions, CourseMember, "_tutor", self.db
        ).filter(
            CourseMember.course_id == course_id,
            CourseMember.user_id == user_id
        ).first()

        if not has_course_perms:
            raise ForbiddenException(
                detail="You don't have permission to view course member grading statistics. "
                       "Tutor role or higher is required."
            )

        # Initialize data repository
        data_repo = CourseMemberGradingsRepository(self.db)

        # Get all course members
        course_members = data_repo.get_all_course_members_with_students_role(course_id)

        if not course_members:
            return []

        # Check if there are any submittable contents in the course
        # If not, don't cache (as per decision: don't cache if no submittable content)
        db_stats_check = data_repo.get_course_level_stats_for_all_members(
            course_id=course_id,
            path_prefix=None,
            course_content_type_id=None,
        )

        if not db_stats_check:
            # No submittable content - return empty stats without caching
            logger.debug(f"No submittable content in course {course_id}, not caching")
            return [
                CourseMemberGradingsList(
                    course_member_id=member["course_member_id"],
                    course_id=str(course_id),
                    user_id=member["user_id"],
                    username=member["username"],
                    given_name=member["given_name"],
                    family_name=member["family_name"],
                    student_id=member["student_id"],
                    total_max_assignments=0,
                    total_submitted_assignments=0,
                    overall_progress_percentage=0.0,
                    latest_submission_at=None,
                    by_content_type=[],
                )
                for member in course_members
            ]

        # Process each member with caching
        results = []
        for member in course_members:
            member_id = member["course_member_id"]

            # Try to get from cache first
            cache_key = f"cm_grading:{member_id}"
            cached_data = self._get_cached_view(
                user_id=str(user_id),
                view_type=cache_key
            )

            if cached_data:
                # Convert cached full data to list format (without nodes)
                # IMPORTANT: Use member dict for user info (always fresh from DB query above)
                list_item = CourseMemberGradingsList(
                    course_member_id=cached_data["course_member_id"],
                    course_id=cached_data["course_id"],
                    user_id=member["user_id"],
                    username=member["username"],
                    given_name=member["given_name"],
                    family_name=member["family_name"],
                    student_id=member["student_id"],
                    total_max_assignments=cached_data["total_max_assignments"],
                    total_submitted_assignments=cached_data["total_submitted_assignments"],
                    overall_progress_percentage=cached_data["overall_progress_percentage"],
                    latest_submission_at=cached_data.get("latest_submission_at"),
                    by_content_type=[ContentTypeGradingStats(**ct) for ct in cached_data["by_content_type"]],
                )
                results.append(list_item)
            else:
                # Cache MISS - calculate for this member
                try:
                    full_stats = await self.get_course_member_gradings(
                        course_member_id=member_id,
                        permissions=permissions,
                        params=params,
                    )
                    # Convert to list format
                    list_item = CourseMemberGradingsList(
                        course_member_id=full_stats.course_member_id,
                        course_id=full_stats.course_id,
                        user_id=member["user_id"],
                        username=member["username"],
                        given_name=member["given_name"],
                        family_name=member["family_name"],
                        student_id=member["student_id"],
                        total_max_assignments=full_stats.total_max_assignments,
                        total_submitted_assignments=full_stats.total_submitted_assignments,
                        overall_progress_percentage=full_stats.overall_progress_percentage,
                        latest_submission_at=full_stats.latest_submission_at,
                        by_content_type=full_stats.by_content_type,
                    )
                    results.append(list_item)
                except Exception as e:
                    logger.error(f"Error calculating stats for member {member_id}: {e}")
                    # Return empty stats on error
                    results.append(CourseMemberGradingsList(
                        course_member_id=member_id,
                        course_id=str(course_id),
                        user_id=member["user_id"],
                        username=member["username"],
                        given_name=member["given_name"],
                        family_name=member["family_name"],
                        student_id=member["student_id"],
                        total_max_assignments=0,
                        total_submitted_assignments=0,
                        overall_progress_percentage=0.0,
                        latest_submission_at=None,
                        by_content_type=[],
                    ))

        return results

    def _process_hierarchical_stats(
        self,
        db_stats: List[Dict[str, Any]],
        path_titles: Dict[str, str],
        assignment_details: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Process raw database statistics into hierarchical structure.

        This is imported from the existing business logic helper.
        """
        from ..business_logic.course_member_gradings import _process_hierarchical_stats
        return _process_hierarchical_stats(db_stats, path_titles, assignment_details)
