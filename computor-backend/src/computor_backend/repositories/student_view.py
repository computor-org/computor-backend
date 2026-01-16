"""
Student view repository for student-specific aggregated queries with caching.

This repository handles complex student-view queries that aggregate data
from multiple tables (courses, course_contents, submissions, results, etc.)
"""

from typing import List, Dict, Optional
from uuid import UUID

from .view_base import ViewRepository, _aggregate_grading_status


from ..api.mappers import course_member_course_content_result_mapper
from ..repositories.course_content import CourseMemberCourseContentQueryResult
from ..repositories.course_content import (
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
    CourseStudentRepository,
)
from computor_backend.interfaces.student_courses import CourseStudentInterface
from ..model.course import Course


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
            status, unreviewed_count = self._aggregate_single_unit_status(user_id, result)
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

    def _aggregate_single_unit_status(
        self,
        user_id: str,
        course_content: CourseContentStudentGet,
    ) -> tuple:
        """
        Aggregate status and unreviewed_count for a single unit-like course content from its descendants.

        This is used for the single GET endpoint where we need to query descendants
        from the database.

        Args:
            user_id: Student user ID
            course_content: The unit course content to aggregate status for

        Returns:
            Tuple of (aggregated_status, total_unreviewed_count)
        """
        # Only aggregate for non-submittable content (units)
        if course_content.submission_group is not None:
            return (course_content.status, course_content.unreviewed_count)

        # Query descendants from the same course with path starting with this unit's path
        from computor_backend.repositories.course_content import user_course_content_list_query
        from sqlalchemy import text

        unit_path = str(course_content.path)

        # Get all course contents for this user in the same course
        # The query already joins to the user's submission group and includes grading status
        query = user_course_content_list_query(user_id, self.db)
        query = query.filter(text("course_content.course_id = :course_id"))
        query = query.params(course_id=str(course_content.course_id))

        all_contents = query.all()

        # Find descendants and collect their statuses
        # Use the status from the query result tuple which is already user-specific
        descendant_statuses: List[str] = []
        total_unreviewed_count = 0
        status_lookup = {
            0: "not_reviewed",
            1: "corrected",
            2: "correction_necessary",
            3: "improvement_possible"
        }

        for row in all_contents:
            # row is a Row/tuple where index 0 is CourseContent
            course_content_obj = row[0]
            row_path = str(course_content_obj.path)

            # Skip self and non-descendants
            if row_path == unit_path or not row_path.startswith(unit_path + '.'):
                continue

            # row[3] is submission_group, row[5] is submission_status_int from the query
            # row[10] is is_unreviewed from the query
            submission_group = row[3]
            submission_status_int = row[5] if len(row) > 5 else None
            is_unreviewed = row[10] if len(row) > 10 else 0

            # Only collect from submittable contents (those with submission_group)
            # If submission_group exists but status is None, treat as not_reviewed
            if submission_group is not None:
                status_str = status_lookup.get(submission_status_int, "not_reviewed") if submission_status_int is not None else "not_reviewed"
                descendant_statuses.append(status_str)
                total_unreviewed_count += is_unreviewed or 0

        if descendant_statuses:
            return (_aggregate_grading_status(descendant_statuses), total_unreviewed_count)

        return (None, 0)

    # Note: _aggregate_unit_statuses and _aggregate_single_unit_status_for_list
    # are inherited from ViewRepository base class

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

        response_list: List[CourseContentStudentList] = []
        for course_contents_result in course_contents_results:
            # Convert tuple to typed model before mapping
            typed_result = CourseMemberCourseContentQueryResult.from_tuple(course_contents_result)
            response_list.append(await course_member_course_content_result_mapper(typed_result, self.db))

        # Aggregate status for unit-like course contents (non-submittable)
        # Units aggregate status from their descendant submittable contents
        response_list = self._aggregate_unit_statuses(response_list, user_id)

        # Cache result with query-aware key
        # CRITICAL: Tag with course_id AND individual course_content IDs for proper invalidation
        related_ids = {}
        if params.course_id:
            # Single course filter - tag with that course_id
            related_ids['student_view'] = str(params.course_id)

        # CRITICAL: Tag each course_content for deployment-related invalidation
        for result in response_list:
            if hasattr(result, 'id') and result.id:
                related_ids[f'course_content:{result.id}'] = None

        self._set_cached_query_view(
            user_id=str(user_id),
            view_type="course_contents",
            params=params,
            data=self._serialize_dto_list(response_list),
            ttl=self.get_default_ttl(),
            related_ids=related_ids if related_ids else None
        )

        return response_list

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
        user_id = permissions.get_user_id_or_throw()

        # Try cache with query-aware key
        cached = self._get_cached_query_view(
            user_id=str(user_id),
            view_type="courses",
            params=params
        )
        if cached is not None:
            return [CourseStudentList.model_validate(item, from_attributes=True) for item in cached]

        # Query from DB with permission filtering
        courses = CourseStudentInterface.search(
            self.db,
            check_course_permissions(permissions, Course, "_student", self.db),
            params
        ).all()

        response_list: List[CourseStudentList] = []
        for course in courses:
            response_list.append(CourseStudentList(
                id=course.id,
                title=course.title,
                course_family_id=course.course_family_id,
                organization_id=course.organization_id,
                path=course.path,
                repository=CourseStudentRepository(
                    provider_url=course.properties.get("gitlab", {}).get("url") if course.properties else None,
                    full_path=course.properties.get("gitlab", {}).get("full_path") if course.properties else None
                ) if course.properties and course.properties.get("gitlab") else None
            ))

        # Cache result with query-aware key
        self._set_cached_query_view(
            user_id=str(user_id),
            view_type="courses",
            params=params,
            data=self._serialize_dto_list(response_list),
            ttl=self.get_default_ttl()
        )

        return response_list

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
        user_id = permissions.get_user_id_or_throw()

        # Try cache
        cached = self._get_cached_view(
            user_id=str(user_id),
            view_type="course",
            view_id=str(course_id)
        )
        if cached is not None:
            return CourseStudentGet.model_validate(cached, from_attributes=True)

        # Query from DB with permission filtering
        course = check_course_permissions(permissions, Course, "_student", self.db).filter(
            Course.id == course_id
        ).first()

        result = CourseStudentGet(
            id=course.id,
            title=course.title,
            course_family_id=course.course_family_id,
            organization_id=course.organization_id,
            course_content_types=course.course_content_types,
            path=course.path,
            repository=CourseStudentRepository(
                provider_url=course.properties.get("gitlab", {}).get("url") if course.properties else None,
                full_path=course.properties.get("gitlab", {}).get("full_path") if course.properties else None
            ) if course.properties and course.properties.get("gitlab") else None
        )

        # Cache result
        related_ids = {
            'course_id': str(course_id),
            'course_family_id': str(course.course_family_id),
            'organization_id': str(course.organization_id)
        }
        self._set_cached_view(
            user_id=str(user_id),
            view_type="course",
            view_id=str(course_id),
            data=self._serialize_dto(result),
            ttl=self.get_default_ttl(),
            related_ids=related_ids
        )

        return result
