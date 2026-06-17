"""
Course member gradings view repository with caching.

This repository handles complex grading statistics queries for course members,
providing aggregated progress data with hierarchical breakdowns.

Caching is per-view (not per-user) since grading data is identical for all
tutors/lecturers viewing the same course or member. A Redis-based lock prevents
concurrent recalculation of the same view (thundering herd protection).
"""

from typing import Optional, List, Any
from uuid import UUID
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
                detail="Grading statistics are being calculated, please try again shortly",
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
                raise NotFoundException(
                    detail="Course member not found",
                    context={"course_member_id": str(course_member_id)},
                )

            # Determine course_id
            course_id = params.course_id or str(course_member.course_id)

            # Check if course_id matches the member's course
            if str(course_member.course_id) != course_id:
                raise NotFoundException(
                    detail="Course member does not belong to the requested course",
                    context={
                        "course_member_id": str(course_member_id),
                        "course_id": str(course_id),
                    },
                )

            # Get organization_id from course for student_profile lookup
            course = self.db.query(Course).filter(Course.id == course_id).first()
            org_id = course.organization_id if course else None

            # Fetch user info and student_id
            member_info = (
                self.db.query(
                    User.id.label("user_id"),
                    User.email.label("username"),
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

            data_repo = CourseMemberGradingsRepository(self.db)
            from ..services.course_member_grading_read import (
                build_course_member_grading_response,
            )
            result = build_course_member_grading_response(
                backend=data_repo,
                course_member_id=course_member_id,
                course_id=course_id,
                member_info=member_info,
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
            raise NotFoundException(
                detail="Course member not found",
                context={"course_member_id": str(course_member_id)},
            )

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
                detail="Course grading statistics are being calculated, please try again shortly",
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
                raise NotFoundException(
                    detail="Course not found",
                    context={"course_id": str(course_id)},
                )

            # Permission check
            self._check_course_list_permissions(permissions, user_id, course_id)

            data_repo = CourseMemberGradingsRepository(self.db)
            from ..services.course_member_grading_read import (
                build_course_member_grading_list_response,
            )
            results = build_course_member_grading_list_response(data_repo, course_id)

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
