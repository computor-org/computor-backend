"""
Student view repository for student-specific aggregated queries with caching.

This repository handles complex student-view queries that aggregate data
from multiple tables (courses, course_contents, submissions, results, etc.)
"""

from typing import List, Dict, Optional
from uuid import UUID

from .view_base import ViewRepository


from .view_mappers import course_member_course_content_result_mapper
from ..repositories.course_content_queries import CourseMemberCourseContentQueryResult
from ..repositories.course_content_queries import (
    user_course_content_query,
    user_course_content_list_query
)
from ..permissions.core import check_course_permissions
from ..permissions.principal import Principal
from computor_types.student_course_contents import (
    CourseContentStudentGet,
    CourseContentStudentList,
    CourseContentStudentQuery,
)
from computor_backend.interfaces.student_course_contents import CourseContentStudentInterface
from computor_types.student_courses import (
    CourseStudentGet,
    CourseStudentList,
    CourseStudentQuery,
)
from computor_backend.interfaces.student_courses import CourseStudentInterface
from ..model.course import Course
from computor_backend.permissions.roles import CourseRole


class StudentViewRepository(ViewRepository):
    """
    Repository for student-specific view queries with caching.

    Handles:
    - Student course content views (with submissions, results, grades)
    - Student course lists with GitLab repository info
    - Permission-filtered queries
    """

    def get_default_ttl(self) -> int:
        """Students get 5-minute cache TTL."""
        return 300  # 5 minutes

    async def get_course_content(
        self,
        user_id: str,
        course_content_id: UUID | str,
    ) -> CourseContentStudentGet:
        """
        Get detailed course content for a student with caching.

        Args:
            user_id: Student user ID
            course_content_id: Course content ID

        Returns:
            Detailed course content with submission/result data
        """
        # Try cache
        cached = self._get_cached_view(
            user_id=str(user_id),
            view_type="course_content",
            view_id=str(course_content_id)
        )
        if cached is not None:
            return CourseContentStudentGet.model_validate(cached, from_attributes=True)

        # Provision submission groups for this user (all courses)
        from computor_backend.repositories.submission_group_provisioning import provision_submission_groups_for_user
        provision_submission_groups_for_user(user_id, None, self.db)

        # Query from DB using existing query function
        course_contents_result = user_course_content_query(user_id, course_content_id, self.db)
        result = await course_member_course_content_result_mapper(course_contents_result, self.db, detailed=True)

        # Aggregate status and unreviewed_count for unit-like course contents (non-submittable)
        if result and result.submission_group is None:
            status, unreviewed_count = self._aggregate_single_unit_status_for_list(user_id, result)
            result.status = status
            result.unreviewed_count = unreviewed_count

        # Cache result
        if result:
            # CRITICAL: Tag with student_view for invalidation when results/submissions change
            # CRITICAL: Tag with course_content for deployment-related invalidation
            related_ids = {
                'course_content_id': str(course_content_id),
                'course_content': str(course_content_id)  # ← For deployment invalidation
            }
            if hasattr(result, 'course_id') and result.course_id:
                related_ids['student_view'] = str(result.course_id)  # ← CRITICAL for invalidation
            if hasattr(result, 'course_family_id') and result.course_family_id:
                related_ids['course_family_id'] = str(result.course_family_id)

            self._set_cached_view(
                user_id=str(user_id),
                view_type="course_content",
                view_id=str(course_content_id),
                data=self._serialize_dto(result),
                ttl=self.get_default_ttl(),
                related_ids=related_ids if related_ids else None
            )

        return result

    # Note: _aggregate_unit_statuses and _aggregate_single_unit_status_for_list
    # (used for both list and single-get aggregation) are inherited from the
    # ViewRepository base class

    async def list_course_contents(
        self,
        user_id: str,
        params: CourseContentStudentQuery,
    ) -> List[CourseContentStudentList]:
        """
        List course contents for a student with caching.

        Args:
            user_id: Student user ID
            params: Query parameters (filters, pagination, etc.)

        Returns:
            List of course contents with submission/result data
        """
        # Try cache with query-aware key
        cached = self._get_cached_query_view(
            user_id=str(user_id),
            view_type="course_contents",
            params=params
        )
        if cached is not None:
            return [CourseContentStudentList.model_validate(item, from_attributes=True) for item in cached]

        # Provision submission groups for this user before querying
        from computor_backend.repositories.submission_group_provisioning import provision_submission_groups_for_user
        provision_submission_groups_for_user(user_id, params.course_id, self.db)

        # Query from DB using existing query function
        query = user_course_content_list_query(user_id, self.db)
        course_contents_results = CourseContentStudentInterface.search(self.db, query, params).all()

        return await self._finalize_course_contents_view(
            course_contents_results,
            reader_user_id=user_id,
            view_type="course_contents",
            params=params,
            aggregate_user_id=user_id,
            base_related_ids={'student_view': str(params.course_id)} if params.course_id else None,
        )

    def list_courses(
        self,
        permissions: Principal,
        params: CourseStudentQuery,
    ) -> List[CourseStudentList]:
        """
        List courses accessible to a student with caching.

        Args:
            permissions: Principal with user permissions
            params: Query parameters

        Returns:
            List of courses with GitLab repository info
        """
        return self._list_cached_course_dtos(
            permissions,
            params,
            role=CourseRole.STUDENT,
            view_type="courses",
            dto_cls=CourseStudentList,
            row_builder=lambda course: CourseStudentList(
                id=course.id,
                title=course.title,
                course_family_id=course.course_family_id,
                organization_id=course.organization_id,
                path=course.path,
            ),
        )

    def get_course(
        self,
        course_id: UUID | str,
        permissions: Principal,
    ) -> CourseStudentGet:
        """
        Get detailed course information for a student with caching.

        Args:
            course_id: Course ID
            permissions: Principal with user permissions

        Returns:
            Detailed course information
        """
        def _build(course):
            result = CourseStudentGet(
                id=course.id,
                title=course.title,
                course_family_id=course.course_family_id,
                organization_id=course.organization_id,
                course_content_types=course.course_content_types,
                path=course.path,
            )
            related_ids = {
                'course_id': str(course_id),
                'course_family_id': str(course.course_family_id),
                'organization_id': str(course.organization_id),
            }
            return result, related_ids

        return self._get_cached_course_dto(
            course_id,
            permissions,
            role=CourseRole.STUDENT,
            view_type="course",
            dto_cls=CourseStudentGet,
            builder=_build,
        )
