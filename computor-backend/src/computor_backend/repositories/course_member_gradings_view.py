"""
Course member gradings view repository with caching.

This repository handles complex grading statistics queries for course members,
providing aggregated progress data with hierarchical breakdowns.

Caching is per-view (not per-user) since grading data is identical for all
tutors/lecturers viewing the same course or member. A Redis-based lock prevents
concurrent recalculation of the same view (thundering herd protection).
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from collections import defaultdict
from sqlalchemy.orm import Session
import logging

from .view_base import ViewRepository
from .course_member_gradings import CourseMemberGradingsRepository
from ..model.course import Course, CourseMember
from ..permissions.principal import Principal
from ..permissions.core import check_course_permissions
from ..exceptions import NotFoundException, ForbiddenException
from ..exceptions import RateLimitException
from computor_types.course_member_gradings import (
    CourseMemberGradingsGet,
    CourseMemberGradingsList,
    CourseMemberGradingsQuery,
    CourseMemberGradingNode,
    ContentTypeGradingStats,
)

logger = logging.getLogger(__name__)

# Lock TTL in seconds — prevents duplicate calculations within this window
_LOCK_TTL = 10


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

    async def _acquire_lock(self, lock_key: str) -> bool:
        """
        Try to acquire a Redis lock using SET NX EX (atomic).

        Returns True if lock was acquired, False if already held.
        """
        from ..redis_cache import get_redis_client
        redis = await get_redis_client()
        try:
            return await redis.set(lock_key, "1", nx=True, ex=_LOCK_TTL)
        except Exception as e:
            logger.warning(f"Redis lock acquire failed for {lock_key}: {e}")
            # If Redis is down, allow the request through (fail-open)
            return True

    async def _release_lock(self, lock_key: str):
        """Release a Redis lock."""
        from ..redis_cache import get_redis_client
        redis = await get_redis_client()
        try:
            await redis.delete(lock_key)
        except Exception as e:
            logger.warning(f"Redis lock release failed for {lock_key}: {e}")

    def _get_shared_cache(self, cache_key: str) -> Optional[Any]:
        """Get from shared (non-user-scoped) cache."""
        if not self._use_cache():
            return None
        return self.cache.get_by_key(self.cache.k("view", cache_key))

    def _set_shared_cache(self, cache_key: str, data: Any, tags: set[str]):
        """Set shared (non-user-scoped) cache with tags."""
        if not self._use_cache():
            return
        full_key = self.cache.k("view", cache_key)
        self.cache.set_with_tags(
            key=full_key,
            payload=data,
            tags=tags,
            ttl=self.get_default_ttl(),
        )
        logger.debug(f"Shared cache SET: {full_key} tags={tags} ttl={self.get_default_ttl()}")

    async def get_course_member_gradings(
        self,
        course_member_id: UUID | str,
        permissions: Principal,
        params: CourseMemberGradingsQuery,
    ) -> CourseMemberGradingsGet:
        """
        Get grading statistics for a specific course member.

        Uses shared (non-user-scoped) cache since grading data is identical
        for all tutors/lecturers. A Redis lock prevents concurrent recalculation.

        Args:
            course_member_id: Course member ID
            permissions: Current user permissions
            params: Query parameters (course_id)

        Returns:
            CourseMemberGradingsGet with full hierarchy

        Raises:
            NotFoundException: If course member not found
            ForbiddenException: If user lacks permissions
            RateLimitException: If calculation is already in progress
        """
        user_id = permissions.get_user_id()

        # Try shared cache FIRST (before any DB access)
        cache_key = f"cm_grading:{course_member_id}"
        cached = self._get_shared_cache(cache_key)

        if cached is not None:
            # Still need to verify permissions on cache hit
            self._check_member_permissions(permissions, user_id, course_member_id, params)
            return CourseMemberGradingsGet(**cached)

        # Cache miss — acquire lock to prevent thundering herd
        lock_key = f"lock:{cache_key}"
        acquired = await self._acquire_lock(lock_key)
        if not acquired:
            raise RateLimitException(
                detail="Grading statistics are being calculated, please try again shortly.",
                retry_after=_LOCK_TTL,
            )

        try:
            # Double-check cache (another request may have just finished)
            cached = self._get_shared_cache(cache_key)
            if cached is not None:
                self._check_member_permissions(permissions, user_id, course_member_id, params)
                return CourseMemberGradingsGet(**cached)

            # Cache miss confirmed — access database (lazy connection)
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

            # Permission check: Admin bypasses, otherwise tutor or higher role required
            if not permissions.is_admin:
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

            # Cache at view level (shared across all users)
            self._set_shared_cache(
                cache_key=cache_key,
                data=result.model_dump(),
                tags={
                    f"course_member_id:{course_member_id}",
                    f"course_id:{course_id}",
                    f"cm_grading:{course_member_id}",
                },
            )

            return result
        finally:
            await self._release_lock(lock_key)

    def _check_member_permissions(
        self,
        permissions: Principal,
        user_id: Any,
        course_member_id: UUID | str,
        params: CourseMemberGradingsQuery,
    ):
        """
        Validate permissions for accessing a course member's grading stats.

        Lightweight check used on cache hits (avoids full DB query flow).
        """
        if permissions.is_admin:
            return

        course_member = self.db.query(CourseMember).filter(
            CourseMember.id == course_member_id
        ).first()

        if course_member is None:
            raise NotFoundException(detail=f"Course member {course_member_id} not found")

        course_id = params.course_id or str(course_member.course_id)

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

    async def list_course_member_gradings(
        self,
        course_id: UUID | str,
        permissions: Principal,
        params: CourseMemberGradingsQuery,
    ) -> List[CourseMemberGradingsList]:
        """
        Get grading statistics for all course members in a course.

        Uses shared (non-user-scoped) cache and a Redis lock to prevent
        concurrent recalculation of the same course view.

        Args:
            course_id: Course ID
            permissions: Current user permissions
            params: Query parameters

        Returns:
            List of CourseMemberGradingsList

        Raises:
            NotFoundException: If course not found
            ForbiddenException: If user lacks permissions
            RateLimitException: If calculation is already in progress
        """
        user_id = permissions.get_user_id()

        # Try shared cache first
        cache_key = f"cm_grading_list:{course_id}"
        cached = self._get_shared_cache(cache_key)
        if cached is not None:
            # Still verify permissions on cache hit
            self._check_course_list_permissions(permissions, user_id, course_id)
            return [CourseMemberGradingsList(**item) for item in cached]

        # Cache miss — acquire lock to prevent thundering herd
        lock_key = f"lock:{cache_key}"
        acquired = await self._acquire_lock(lock_key)
        if not acquired:
            raise RateLimitException(
                detail="Course grading statistics are being calculated, please try again shortly.",
                retry_after=_LOCK_TTL,
            )

        try:
            # Double-check cache (another request may have just finished)
            cached = self._get_shared_cache(cache_key)
            if cached is not None:
                self._check_course_list_permissions(permissions, user_id, course_id)
                return [CourseMemberGradingsList(**item) for item in cached]

            # Cache miss confirmed — verify course exists
            course = self.db.query(Course).filter(Course.id == course_id).first()
            if course is None:
                raise NotFoundException(detail=f"Course {course_id} not found")

            # Permission check
            self._check_course_list_permissions(permissions, user_id, course_id)

            # Single bulk query: returns per-member, per-content-type stats
            data_repo = CourseMemberGradingsRepository(self.db)
            db_stats = data_repo.get_course_level_stats_for_all_members(
                course_id=course_id,
                path_prefix=None,
                course_content_type_id=None,
            )

            if not db_stats:
                # No submittable content — return members with empty stats
                course_members = data_repo.get_all_course_members_with_students_role(course_id)
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

            # Aggregate the flat per-member-per-type rows into per-member results
            members_data: dict = {}  # course_member_id -> member info
            members_ct: dict = defaultdict(list)  # course_member_id -> [content_type rows]

            for row in db_stats:
                mid = row["course_member_id"]
                if mid not in members_data:
                    members_data[mid] = {
                        "course_member_id": mid,
                        "course_id": str(course_id),
                        "user_id": row.get("user_id"),
                        "username": row.get("username"),
                        "given_name": row.get("given_name"),
                        "family_name": row.get("family_name"),
                        "student_id": row.get("student_id"),
                    }
                members_ct[mid].append(row)

            results = []
            for mid, member_info in members_data.items():
                ct_rows = members_ct[mid]

                total_max = 0
                total_submitted = 0
                total_graded = 0
                total_grade_sum = 0.0
                latest_submission = None
                by_content_type = []

                for ct_row in ct_rows:
                    max_a = ct_row["max_assignments"]
                    sub_a = ct_row["submitted_assignments"]
                    graded_a = ct_row.get("graded_assignments", 0) or 0
                    avg_g = ct_row.get("average_grading")
                    latest_at = ct_row.get("latest_submission_at")

                    total_max += max_a
                    total_submitted += sub_a
                    total_graded += graded_a
                    if avg_g is not None and graded_a > 0:
                        total_grade_sum += avg_g * graded_a

                    if latest_at and (latest_submission is None or latest_at > latest_submission):
                        latest_submission = latest_at

                    by_content_type.append(ContentTypeGradingStats(
                        course_content_type_id=ct_row["content_type_id"],
                        course_content_type_slug=ct_row["content_type_slug"],
                        course_content_type_title=ct_row.get("content_type_title"),
                        course_content_type_color=ct_row.get("content_type_color"),
                        max_assignments=max_a,
                        submitted_assignments=sub_a,
                        progress_percentage=round((sub_a / max_a * 100) if max_a > 0 else 0.0, 2),
                        graded_assignments=graded_a,
                        average_grading=round(avg_g, 4) if avg_g is not None else None,
                    ))

                overall_progress = round((total_submitted / total_max * 100) if total_max > 0 else 0.0, 2)
                overall_avg = round(total_grade_sum / total_graded, 4) if total_graded > 0 else None

                results.append(CourseMemberGradingsList(
                    **member_info,
                    total_max_assignments=total_max,
                    total_submitted_assignments=total_submitted,
                    overall_progress_percentage=overall_progress,
                    latest_submission_at=latest_submission,
                    overall_average_grading=overall_avg,
                    by_content_type=by_content_type,
                ))

            # Cache at view level (shared across all users)
            self._set_shared_cache(
                cache_key=cache_key,
                data=[r.model_dump() for r in results],
                tags={
                    f"course_id:{course_id}",
                    f"cm_grading_list:{course_id}",
                },
            )

            return results
        finally:
            await self._release_lock(lock_key)

    def _check_course_list_permissions(
        self,
        permissions: Principal,
        user_id: Any,
        course_id: UUID | str,
    ):
        """
        Validate permissions for accessing course-level grading list.

        Lightweight check used on cache hits.
        """
        if permissions.is_admin:
            return

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
