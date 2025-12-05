"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.student_course_contents import (
    CourseContentStudentGet,
    CourseContentStudentList,
)
from computor_types.tutor_course_members import (
    TutorCourseMemberGet,
    TutorCourseMemberList,
)
from computor_types.tutor_courses import (
    CourseTutorGet,
    CourseTutorList,
)
from computor_types.tutor_grading import (
    TutorGradeCreate,
    TutorGradeResponse,
)
from computor_types.tutor_submission_groups import (
    TutorSubmissionGroupGet,
    TutorSubmissionGroupList,
)

from computor_client.http import AsyncHTTPClient


class TutorsClient:
    """
    Client for tutors endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def get_course_members_course_contents(
        self,
        course_member_id: str,
        course_content_id: str,
        **kwargs: Any,
    ) -> CourseContentStudentGet:
        """Tutor Get Course Contents Endpoint"""
        response = await self._http.get(f"/tutors/course-members/{course_member_id}/course-contents/{course_content_id}", params=kwargs)
        return CourseContentStudentGet.model_validate(response.json())

    async def course_members_course_contents(
        self,
        course_member_id: str,
        course_content_id: str,
        data: Union[TutorGradeCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> TutorGradeResponse:
        """Tutor Update Course Contents Endpoint"""
        response = await self._http.patch(f"/tutors/course-members/{course_member_id}/course-contents/{course_content_id}", json_data=data, params=kwargs)
        return TutorGradeResponse.model_validate(response.json())

    async def get_urse_member_id_course_contents(
        self,
        course_member_id: str,
        **kwargs: Any,
    ) -> List[CourseContentStudentList]:
        """Tutor List Course Contents Endpoint"""
        response = await self._http.get(f"/tutors/course-members/{course_member_id}/course-contents", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [CourseContentStudentList.model_validate(item) for item in data]
        return []

    async def courses(
        self,
        course_id: str,
        **kwargs: Any,
    ) -> CourseTutorGet:
        """Tutor Get Courses Endpoint"""
        response = await self._http.get(f"/tutors/courses/{course_id}", params=kwargs)
        return CourseTutorGet.model_validate(response.json())

    async def get_courses(
        self,
        **kwargs: Any,
    ) -> List[CourseTutorList]:
        """Tutor List Courses Endpoint"""
        response = await self._http.get(f"/tutors/courses", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [CourseTutorList.model_validate(item) for item in data]
        return []

    async def course_members(
        self,
        course_member_id: str,
        **kwargs: Any,
    ) -> TutorCourseMemberGet:
        """Tutor Get Course Members Endpoint"""
        response = await self._http.get(f"/tutors/course-members/{course_member_id}", params=kwargs)
        return TutorCourseMemberGet.model_validate(response.json())

    async def get_course_members(
        self,
        **kwargs: Any,
    ) -> List[TutorCourseMemberList]:
        """Tutor List Course Members Endpoint"""
        response = await self._http.get(f"/tutors/course-members", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [TutorCourseMemberList.model_validate(item) for item in data]
        return []

    async def submission_groups(
        self,
        submission_group_id: str,
        **kwargs: Any,
    ) -> TutorSubmissionGroupGet:
        """Tutor Get Submission Group Endpoint"""
        response = await self._http.get(f"/tutors/submission-groups/{submission_group_id}", params=kwargs)
        return TutorSubmissionGroupGet.model_validate(response.json())

    async def get_submission_groups(
        self,
        **kwargs: Any,
    ) -> List[TutorSubmissionGroupList]:
        """Tutor List Submission Groups Endpoint"""
        response = await self._http.get(f"/tutors/submission-groups", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [TutorSubmissionGroupList.model_validate(item) for item in data]
        return []

    async def course_contents_reference(
        self,
        course_content_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Download Course Content Reference"""
        response = await self._http.get(f"/tutors/course-contents/{course_content_id}/reference", params=kwargs)
        return response.json()

