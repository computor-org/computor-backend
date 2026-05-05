"""
Lecturer view repository for lecturer-specific aggregated queries with caching.

This repository handles complex lecturer-view queries for course management
and course content with GitLab repository information.
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session, joinedload

from .view_base import ViewRepository
from .course import CourseRepository
from ..permissions.core import check_course_permissions
from ..permissions.principal import Principal
from ..exceptions import NotFoundException
from computor_types.courses import CourseList, CourseQuery
from computor_backend.interfaces.course import CourseInterface
from computor_types.lecturer_course_contents import (
    CourseContentLecturerGet,
    CourseContentLecturerList,
    CourseContentLecturerQuery,
)
from computor_types.deployment import CourseContentDeploymentList
from computor_backend.interfaces.lecturer_course_contents import CourseContentLecturerInterface
from ..model.course import Course, CourseContent
from ..model.deployment import CourseContentDeployment


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
        # CRITICAL: Tag with lecturer_view for invalidation when results/submissions change
        self._set_cached_view(
            user_id=str(user_id),
            view_type="lecturer:course_content",
            view_id=str(course_content_id),
            data=self._serialize_dto(result),
            ttl=self.get_default_ttl(),
            related_ids={
                'course_content_id': str(course_content_id),
                'lecturer_view': str(course_content.course_id)  # ← CRITICAL for invalidation
            }
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

        # Eager-load deployment and its example_version to avoid N+1 queries
        query = query.options(
            joinedload(CourseContent.deployment).joinedload(CourseContentDeployment.example_version)
        )

        # Apply search filters
        course_contents = CourseContentLecturerInterface.search(self.db, query, params)

        # Batch-compute has_newer_version for all deployments
        newer_version_map = self._compute_has_newer_version_batch(course_contents)

        # Use CourseRepository with cache for efficient course lookups
        course_repo = CourseRepository(self.db, self.cache)

        # Build response with course repository info for each item
        result = []
        for course_content in course_contents:
            # Get the course to extract GitLab repository information (cached)
            course = course_repo.get_by_id_optional(course_content.course_id)

            # Safely extract GitLab properties (handle dict or None)
            gitlab_props = {}
            if course and course.properties:
                # Ensure properties is a dict (defensive check for cached data)
                if isinstance(course.properties, dict):
                    gitlab_props = course.properties.get("gitlab", {})
                elif isinstance(course.properties, str):
                    # Handle legacy stringified properties from old cache
                    try:
                        import json
                        props = json.loads(course.properties)
                        gitlab_props = props.get("gitlab", {})
                    except Exception:
                        gitlab_props = {}

            # Build deployment DTO if deployment exists
            deployment_dto = None
            dep = course_content.deployment
            if dep and dep.deployment_status != 'unassigned':
                deployment_dto = CourseContentDeploymentList(
                    id=str(dep.id),
                    course_content_id=str(dep.course_content_id),
                    example_version_id=str(dep.example_version_id) if dep.example_version_id else None,
                    example_identifier=str(dep.example_identifier) if dep.example_identifier else None,
                    version_tag=dep.version_tag,
                    deployment_status=dep.deployment_status,
                    assigned_at=dep.assigned_at,
                    deployed_at=dep.deployed_at,
                    version_identifier=dep.version_identifier,
                    has_newer_version=newer_version_map.get(str(course_content.id), False),
                    example_version=dep.example_version,
                )

            response_dict = {
                **course_content.__dict__,
                "has_deployment": course_content.has_deployment,
                "deployment_status": course_content.deployment_status,
                "deployment": deployment_dto,
                "repository": {
                    "url": gitlab_props.get("url") if isinstance(gitlab_props, dict) else None,
                    "full_path": gitlab_props.get("full_path") if isinstance(gitlab_props, dict) else None
                }
            }

            result.append(CourseContentLecturerList.model_validate(response_dict))

        # Cache result with query-aware key
        # CRITICAL: Extract course_ids for proper invalidation
        course_ids = {}
        if params.course_id:
            # Single course filter - tag with that course_id
            course_ids = {'lecturer_view': str(params.course_id)}

        self._set_cached_query_view(
            user_id=str(user_id),
            view_type="lecturer:course_contents",
            params=params,
            data=self._serialize_dto_list(result),
            ttl=self.get_default_ttl(),
            related_ids=course_ids if course_ids else None
        )

        return result

    def _compute_has_newer_version_batch(
        self,
        course_contents: list,
    ) -> dict[str, bool]:
        """
        Batch-compute has_newer_version for all course contents with deployments.

        Returns:
            dict mapping course_content_id (str) → bool
        """
        from sqlalchemy import func
        from ..model.example import ExampleVersion

        # Collect example_ids from deployments that have example_version loaded
        example_version_map: dict[str, tuple[str, int]] = {}  # content_id → (example_id, version_number)
        example_ids: set[str] = set()

        for cc in course_contents:
            dep = cc.deployment
            if dep and dep.example_version and dep.example_version.example_id:
                eid = str(dep.example_version.example_id)
                example_ids.add(eid)
                example_version_map[str(cc.id)] = (eid, dep.example_version.version_number)

        if not example_ids:
            return {}

        # Single query to get latest version_number per example_id
        latest_subq = self.db.query(
            ExampleVersion.example_id,
            func.max(ExampleVersion.version_number).label('max_vn')
        ).filter(
            ExampleVersion.example_id.in_(list(example_ids))
        ).group_by(ExampleVersion.example_id).subquery()

        latest_versions = self.db.query(
            latest_subq.c.example_id,
            latest_subq.c.max_vn,
        ).all()

        latest_map = {str(row[0]): row[1] for row in latest_versions}

        # Compare each deployment's version_number against the latest
        result: dict[str, bool] = {}
        for content_id, (example_id, current_vn) in example_version_map.items():
            latest_vn = latest_map.get(example_id)
            result[content_id] = latest_vn is not None and latest_vn > current_vn

        return result
