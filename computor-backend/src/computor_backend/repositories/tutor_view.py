"""
Tutor view repository for tutor-specific aggregated queries with caching.

This repository handles complex tutor-view queries for viewing student
submissions, grading, and course member management.
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from .view_base import ViewRepository
from .view_mappers import course_member_course_content_result_mapper
from ..repositories.course_content_queries import (
    course_member_course_content_query,
    course_member_course_content_list_query,
    CourseMemberCourseContentQueryResult,
)
from ..permissions.core import check_course_permissions
from ..permissions.principal import Principal
from ..exceptions import ForbiddenException
from computor_types.student_courses import CourseStudentQuery
from computor_backend.interfaces.student_courses import CourseStudentInterface
from computor_types.student_course_contents import CourseContentStudentQuery
from computor_backend.interfaces.student_course_contents import CourseContentStudentInterface
from computor_types.tutor_courses import CourseTutorGet, CourseTutorList, CourseTutorRepository
from ..model.course import Course, CourseMember


class TutorViewRepository(ViewRepository):
    """
    Repository for tutor-specific view queries with caching.

    Handles:
    - Tutor views of student course content (for grading)
    - Tutor course lists
    - Course member views for tutors
    """

    def get_default_ttl(self) -> int:
        """Tutors get 3-minute cache TTL (fresher data for grading)."""
        return 180  # 3 minutes

    async def get_course_content(
        self,
        course_member_id: UUID | str,
        course_content_id: UUID | str,
        permissions: Principal,
    ):
        """
        Get course content for a course member as a tutor (for grading).

        Args:
            course_member_id: Student course member ID
            course_content_id: Course content ID
            permissions: Tutor principal

        Returns:
            Course content with submission/grading data
        """
        reader_user_id = permissions.get_user_id_or_throw()

        # Try cache FIRST (before any DB access)
        cache_key = f"tutor:member:{course_member_id}:content:{course_content_id}"

        cached = self._get_cached_view(
            user_id=str(reader_user_id),
            view_type=cache_key
        )
        if cached is not None:
            return cached

        # Cache miss - now do permission check (requires DB)
        course_member = check_course_permissions(permissions, CourseMember, "_tutor", self.db).filter(
            CourseMember.id == course_member_id
        ).first()

        if course_member is None:
            raise ForbiddenException()

        # Query from DB
        course_contents_result = course_member_course_content_query(
            course_member_id, course_content_id, self.db, reader_user_id=reader_user_id
        )
        result = await course_member_course_content_result_mapper(course_contents_result, self.db, detailed=True)

        # Cache result
        if result:
            # CRITICAL: Tag with submission_group_id for proper invalidation
            # CRITICAL: Tag with course_content for deployment-related invalidation
            # When artifacts/results change, they have submission_group_id, so we tag with that
            related_ids = {
                'course_member_id': str(course_member_id),
                'course_content_id': str(course_content_id),
                'course_content': str(course_content_id),  # ← For deployment invalidation
                'tutor_view': str(course_member.course_id)  # Course-level invalidation
            }

            # Extract submission_group_id if available in result
            if hasattr(result, 'submission_group_id') and result.submission_group_id:
                related_ids['submission_group'] = str(result.submission_group_id)

            self._set_cached_view(
                user_id=str(reader_user_id),
                view_type=cache_key,
                data=self._serialize_dto(result),
                ttl=self.get_default_ttl(),
                related_ids=related_ids
            )

        return result

    async def list_course_contents(
        self,
        course_member_id: UUID | str,
        permissions: Principal,
        params: CourseContentStudentQuery,
    ):
        """
        List course contents for a course member as a tutor.

        Args:
            course_member_id: Student course member ID
            permissions: Tutor principal
            params: Query parameters

        Returns:
            List of course contents with submission data
        """
        reader_user_id = permissions.get_user_id_or_throw()

        # Try cache FIRST (before any DB access)
        cached = self._get_cached_query_view(
            user_id=str(reader_user_id),
            view_type=f"tutor:course_contents:member:{course_member_id}",
            params=params
        )
        if cached is not None:
            return cached

        # Cache miss - now do permission check (requires DB)
        course_member = check_course_permissions(permissions, CourseMember, "_tutor", self.db).filter(
            CourseMember.id == course_member_id
        ).first()

        if course_member is None:
            raise ForbiddenException()

        # Query from DB
        query = course_member_course_content_list_query(course_member_id, self.db, reader_user_id=reader_user_id)
        course_contents_results = CourseContentStudentInterface.search(self.db, query, params).all()

        return await self._finalize_course_contents_view(
            course_contents_results,
            reader_user_id=reader_user_id,
            view_type=f"tutor:course_contents:member:{course_member_id}",
            params=params,
            aggregate_user_id=str(course_member.user_id),
            base_related_ids={
                'course_member_id': str(course_member_id),
                'tutor_view': str(course_member.course_id),
            },
        )

    def get_course(
        self,
        course_id: UUID | str,
        permissions: Principal,
    ) -> CourseTutorGet:
        """
        Get a course for tutors with caching.

        Args:
            course_id: Course ID
            permissions: Tutor principal

        Returns:
            Course with tutor-specific info
        """
        def _build(course):
            gitlab_props = course.properties.get("gitlab", {}) if course.properties else {}
            gitlab_projects = gitlab_props.get("projects", {})
            result = CourseTutorGet(
                id=str(course.id),
                title=course.title,
                course_family_id=str(course.course_family_id) if course.course_family_id else None,
                organization_id=str(course.organization_id) if course.organization_id else None,
                path=course.path,
                repository=CourseTutorRepository(
                    provider_url=gitlab_props.get("url"),
                    full_path_assignments=gitlab_projects.get("assignments", {}).get("full_path"),
                    full_path_student_template=gitlab_projects.get("student_template", {}).get("full_path"),
                ) if gitlab_props else None,
            )
            return result, {'course_id': str(course_id)}

        return self._get_cached_course_dto(
            course_id,
            permissions,
            role="_tutor",
            view_type="tutor:course",
            dto_cls=CourseTutorGet,
            builder=_build,
            raise_if_missing=True,
        )

    def list_courses(
        self,
        permissions: Principal,
        params: CourseStudentQuery,
    ) -> List[CourseTutorList]:
        """
        List courses for tutors with caching.

        Args:
            permissions: Tutor principal
            params: Query parameters

        Returns:
            List of courses accessible to tutor
        """
        def _build_row(course) -> CourseTutorList:
            gitlab_props = course.properties.get("gitlab", {}) if course.properties else {}
            gitlab_projects = gitlab_props.get("projects", {})
            return CourseTutorList(
                id=str(course.id),
                title=course.title,
                course_family_id=str(course.course_family_id) if course.course_family_id else None,
                organization_id=str(course.organization_id) if course.organization_id else None,
                path=course.path,
                repository=CourseTutorRepository(
                    provider_url=gitlab_props.get("url"),
                    full_path_assignments=gitlab_projects.get("assignments", {}).get("full_path"),
                    full_path_student_template=gitlab_projects.get("student_template", {}).get("full_path"),
                ) if gitlab_props else None,
            )

        return self._list_cached_course_dtos(
            permissions,
            params,
            role="_tutor",
            view_type="tutor:courses",
            dto_cls=CourseTutorList,
            row_builder=_build_row,
        )
