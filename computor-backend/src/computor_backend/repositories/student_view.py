"""
Student view repository for student-specific aggregated queries with caching.

This repository handles complex student-view queries that aggregate data
from multiple tables (courses, course_contents, submissions, results, etc.)
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from .view_base import ViewRepository


from .view_mappers import course_member_course_content_result_mapper
from ..repositories.course_content_queries import CourseMemberCourseContentQueryResult
from ..repositories.course_content_queries import (
    user_course_content_query,
    user_course_content_list_query
)
from ..permissions.core import check_course_permissions
from ..permissions.course_access import is_course_staff
from ..permissions.principal import Principal
from ..business_logic.content_visibility import is_content_released, is_content_visible
from computor_types.student_course_contents import (
    CourseContentStudentGet,
    CourseContentStudentList,
    CourseContentStudentQuery,
)
from computor_backend.interfaces.student_course_contents import CourseContentStudentInterface
from computor_types.grading import GradingStatus
from computor_types.student_courses import (
    CourseStudentGet,
    CourseStudentList,
    CourseStudentQuery,
)
from computor_backend.interfaces.student_courses import CourseStudentInterface
from ..model.course import Course, CourseContent, CourseMember
from ..exceptions import BadRequestException, NotFoundException
from computor_backend.permissions.roles import CourseRole


def _parse_grading_statuses(raw: Optional[str]) -> Optional[list[int]]:
    """``"correction_necessary,corrected"`` -> ``[2, 1]``.

    Rejects an unknown slug rather than filtering on nothing: a typo that
    silently returned an empty list would look like "you have no work to do".
    """
    if not raw:
        return None
    values: list[int] = []
    for token in raw.split(","):
        if not token.strip():
            continue
        status = GradingStatus.from_slug(token)
        if status is None:
            raise BadRequestException(
                detail=(
                    f"Unknown grading status {token.strip()!r}. Expected one of: "
                    + ", ".join(s.to_slug() for s in GradingStatus)
                )
            )
        values.append(int(status))
    return values or None


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

    def _may_see_hidden(
        self,
        permissions: Optional[Principal],
        course_id: UUID | str | None,
    ) -> bool:
        """Whether this caller keeps content hidden from students (issue #338).

        A lecturer or tutor who is also enrolled walks this very view to
        rehearse an exam as a student, so they must still receive the hidden
        rows -- marked, not dropped. Everyone else loses them.

        Without a principal or a course to scope the check to, the answer is
        no: the safe default is to hide.
        """
        if permissions is None or course_id is None:
            return False
        return is_course_staff(permissions, course_id, self.db)

    def _guard_hidden_content(
        self,
        result,
        permissions: Optional[Principal],
    ) -> None:
        """404 a single course content the caller is not allowed to see.

        The list path filters in SQL; this is its single-row counterpart, for
        ``GET /students/course-contents/{id}`` which never goes through
        ``search()``. ``visible_effective`` is set either way so a staff caller
        gets the row marked rather than dropped.

        Two things drop a row here, and only one of them is ``visible_effective``:
        a lecturer hiding it (#338) and an assignment never released (#163).
        The second is deliberately not written into the flag -- the staff trees
        grey rows by it, and an undeployed assignment is unfinished, not hidden.
        """
        content = self.db.query(CourseContent).filter(
            CourseContent.id == result.id
        ).first()
        if content is None:
            return

        visible = is_content_visible(self.db, content)
        result.visible_effective = visible

        if visible and is_content_released(self.db, content):
            return

        if not self._may_see_hidden(permissions, result.course_id):
            raise NotFoundException()

    async def get_course_content(
        self,
        user_id: str,
        course_content_id: UUID | str,
        permissions: Optional[Principal] = None,
    ) -> CourseContentStudentGet:
        """
        Get detailed course content for a student with caching.

        Args:
            user_id: Student user ID
            course_content_id: Course content ID
            permissions: Caller principal; staff still get hidden content.

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

        # This path bypasses CourseContentStudentInterface.search entirely, so
        # it needs its own visibility guard (issue #338). 404 rather than 403:
        # a student should not learn that a hidden assignment exists.
        if result is not None:
            self._guard_hidden_content(result, permissions)

        # Aggregate status and unreviewed_count for unit-like course contents (non-submittable)
        if result and result.submission_group is None:
            status, unreviewed_count = self._aggregate_single_unit_status_for_list(
                user_id,
                result,
                include_hidden=self._may_see_hidden(permissions, result.course_id),
            )
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
        permissions: Optional[Principal] = None,
    ) -> List[CourseContentStudentList]:
        """
        List course contents for a student with caching.

        Args:
            user_id: Student user ID
            params: Query parameters (filters, pagination, etc.)
            permissions: Caller principal, used only to decide whether hidden
                content is returned (issue #338). Staff keep it, students do
                not. Cache entries are keyed per user, so the two never mix.

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

        include_hidden = self._may_see_hidden(permissions, params.course_id)

        # Query from DB using existing query function
        query = user_course_content_list_query(
            user_id, self.db, grading_statuses=_parse_grading_statuses(params.status)
        )
        course_contents_results = CourseContentStudentInterface.search(
            self.db, query, params, include_hidden=include_hidden
        ).all()

        return await self._finalize_course_contents_view(
            course_contents_results,
            reader_user_id=user_id,
            view_type="course_contents",
            params=params,
            aggregate_user_id=user_id,
            base_related_ids=self._course_content_view_tags(user_id, params.course_id),
            include_hidden=include_hidden,
        )

    def _course_content_view_tags(
        self,
        user_id: UUID | str,
        course_id: UUID | str | None,
    ) -> Optional[Dict[str, Any]]:
        """Cache tags for a cached course-contents listing.

        Scoped to one course, that is just this user's view of it. Unscoped —
        ``course_id`` omitted, which the endpoint allows and the dashboard uses
        to ask "what needs my attention across every course" — the answer spans
        every course the user is enrolled in, so it has to be tagged with all of
        them. Otherwise a tutor grading in course A invalidates only the tags
        carrying A's id, and the cross-course entry, which carried no course tag
        at all, kept serving the pre-grade answer for the rest of its TTL.

        Tags with a None value are emitted verbatim (see Cache.set_user_view),
        which is what lets one key carry N courses.
        """
        if course_id is not None:
            return {'student_view': str(course_id)}

        course_ids = [
            str(row[0])
            for row in self.db.query(CourseMember.course_id)
            .filter(CourseMember.user_id == str(user_id))
            .distinct()
            .all()
        ]
        if not course_ids:
            return None

        tags: Dict[str, Any] = {}
        for cid in course_ids:
            # Both spellings: `student_view:<id>` is what the grading path emits
            # for student-facing views, `course_id:<id>` is the generic user-view
            # tag every ViewRepository auto-attaches when the id is in the params.
            tags[f'student_view:{cid}'] = None
            tags[f'course_id:{cid}'] = None
        return tags

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
                description=course.description,
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
                description=course.description,
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
