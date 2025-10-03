"""
Lecturer view repository for lecturer-specific aggregated queries with caching.

This repository handles complex lecturer-view queries for course management
and course content with GitLab repository information.
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from .view_base import ViewRepository
from .course import CourseRepository
from ..permissions.core import check_course_permissions
from ..permissions.principal import Principal
from ..api.exceptions import NotFoundException
from ..interface.courses import CourseInterface, CourseList, CourseQuery
from ..interface.lecturer_course_contents import (
    CourseContentLecturerGet,
    CourseContentLecturerList,
    CourseContentLecturerQuery,
    CourseContentLecturerInterface
)
from ..model.course import Course, CourseContent


class LecturerViewRepository(ViewRepository):
    """
    Repository for lecturer-specific view queries with caching.

    Handles:
    - Lecturer course views
    - Course content views with GitLab repository information
    """

    def get_default_ttl(self) -> int:
        """Lecturers get 5-minute cache TTL."""
        return 300  # 5 minutes

    def get_course(
        self,
        course_id: UUID | str,
        permissions: Principal,
    ) -> Course:
        """
        Get a specific course for lecturers with caching.

        Args:
            course_id: Course ID
            permissions: Lecturer principal

        Returns:
            Course entity
        """
        user_id = permissions.get_user_id_or_throw()

        # Try cache
        cached = self._get_cached_view(
            user_id=str(user_id),
            view_type="lecturer:course",
            view_id=str(course_id)
        )
        if cached is not None:
            return Course(**cached) if isinstance(cached, dict) else cached

        # Query from DB
        course = check_course_permissions(permissions, Course, "_lecturer", self.db).filter(
            Course.id == course_id
        ).first()

        if course is None:
            raise NotFoundException()

        # Cache result
        self._set_cached_view(
            user_id=str(user_id),
            view_type="lecturer:course",
            view_id=str(course_id),
            data={k: v for k, v in course.__dict__.items() if not k.startswith('_')},
            ttl=self.get_default_ttl(),
            related_ids={'course_id': str(course_id)}
        )

        return course

    def list_courses(
        self,
        permissions: Principal,
        params: CourseQuery,
    ) -> List[CourseList]:
        """
        List courses accessible to lecturers with caching.

        Args:
            permissions: Lecturer principal
            params: Query parameters

        Returns:
            List of courses
        """
        user_id = permissions.get_user_id_or_throw()

        # Try cache with query-aware key
        cached = self._get_cached_query_view(
            user_id=str(user_id),
            view_type="lecturer:courses",
            params=params
        )
        if cached is not None:
            return [CourseList.model_validate(item, from_attributes=True) for item in cached]

        # Query from DB
        query = check_course_permissions(permissions, Course, "_lecturer", self.db)
        result = CourseInterface.search(self.db, query, params)

        # Cache result with query-aware key
        self._set_cached_query_view(
            user_id=str(user_id),
            view_type="lecturer:courses",
            params=params,
            data=[item.model_dump() if hasattr(item, 'model_dump') else {k: v for k, v in item.__dict__.items() if not k.startswith('_')} for item in result],
            ttl=self.get_default_ttl()
        )

        return result

    def get_course_content(
        self,
        course_content_id: UUID | str,
        permissions: Principal,
    ) -> CourseContentLecturerGet:
        """
        Get a specific course content with course repository information.

        Args:
            course_content_id: Course content ID
            permissions: Lecturer principal

        Returns:
            Course content with GitLab repository info
        """
        user_id = permissions.get_user_id_or_throw()

        # Try cache
        cached = self._get_cached_view(
            user_id=str(user_id),
            view_type="lecturer:course_content",
            view_id=str(course_content_id)
        )
        if cached is not None:
            return CourseContentLecturerGet.model_validate(cached, from_attributes=True)

        # Check permissions and get course content
        course_content = check_course_permissions(
            permissions, CourseContent, "_lecturer", self.db
        ).filter(CourseContent.id == course_content_id).first()

        if course_content is None:
            raise NotFoundException()

        # Use CourseRepository to get course with caching
        course_repo = CourseRepository(self.db, self.cache)
        course = course_repo.get_by_id_optional(course_content.course_id)

        # Build response with course repository info
        response_dict = {
            **course_content.__dict__,
            "repository": {
                "url": course.properties.get("gitlab", {}).get("url") if course.properties else None,
                "full_path": course.properties.get("gitlab", {}).get("full_path") if course.properties else None
            }
        }

        result = CourseContentLecturerGet.model_validate(response_dict)

        # Cache result
        self._set_cached_view(
            user_id=str(user_id),
            view_type="lecturer:course_content",
            view_id=str(course_content_id),
            data=self._serialize_dto(result),
            ttl=self.get_default_ttl(),
            related_ids={'course_content_id': str(course_content_id), 'course_id': str(course_content.course_id)}
        )

        return result

    def list_course_contents(
        self,
        permissions: Principal,
        params: CourseContentLecturerQuery,
    ) -> List[CourseContentLecturerList]:
        """
        List course contents with course repository information.

        Args:
            permissions: Lecturer principal
            params: Query parameters

        Returns:
            List of course contents with GitLab repository info
        """
        user_id = permissions.get_user_id_or_throw()

        # Try cache with query-aware key
        cached = self._get_cached_query_view(
            user_id=str(user_id),
            view_type="lecturer:course_contents",
            params=params
        )
        if cached is not None:
            return [CourseContentLecturerList.model_validate(item, from_attributes=True) for item in cached]

        # Check permissions
        query = check_course_permissions(
            permissions, CourseContent, "_lecturer", self.db
        )

        # Apply search filters
        course_contents = CourseContentLecturerInterface.search(self.db, query, params)

        # Use CourseRepository with cache for efficient course lookups
        course_repo = CourseRepository(self.db, self.cache)

        # Build response with course repository info for each item
        result = []
        for course_content in course_contents:
            # Get the course to extract GitLab repository information (cached)
            course = course_repo.get_by_id_optional(course_content.course_id)

            response_dict = {
                **course_content.__dict__,
                "repository": {
                    "url": course.properties.get("gitlab", {}).get("url") if course.properties else None,
                    "full_path": course.properties.get("gitlab", {}).get("full_path") if course.properties else None
                }
            }

            result.append(CourseContentLecturerList.model_validate(response_dict))

        # Cache result with query-aware key
        self._set_cached_query_view(
            user_id=str(user_id),
            view_type="lecturer:course_contents",
            params=params,
            data=self._serialize_dto_list(result),
            ttl=self.get_default_ttl()
        )

        return result
