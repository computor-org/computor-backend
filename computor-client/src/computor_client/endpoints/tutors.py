"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
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
    TutorSubmissionGroupLimitsUpdate,
    TutorSubmissionGroupList,
)
from computor_types.tutor_tests import (
    TutorTestArtifactList,
    TutorTestCreateResponse,
    TutorTestGet,
    TutorTestResultSubmit,
    TutorTestStatus,
)

from computor_client.http import AsyncHTTPClient
from computor_client.urls import quote_path


class TutorsClient:
    """
    Client for tutors endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def get_course_contents_description(
        self,
        course_content_id: str,
        **kwargs: Any,
    ) -> bytes:
        """Download Course Content Description"""
        response = await self._http.get(f"/tutors/course-contents/{quote_path(course_content_id)}/description", params=kwargs)
        return response.content

    async def get_course_contents_reference(
        self,
        course_content_id: str,
        **kwargs: Any,
    ) -> bytes:
        """Download Course Content Reference"""
        response = await self._http.get(f"/tutors/course-contents/{quote_path(course_content_id)}/reference", params=kwargs)
        return response.content

    async def course_contents_test(
        self,
        course_content_id: str,
        file: bytes,
        config: Optional[str] = None,
        **kwargs: Any,
    ) -> TutorTestCreateResponse:
        """Create Tutor Test"""
        files = {"file": file}
        form_fields = {k: v for k, v in {"config": config}.items() if v is not None}
        response = await self._http.post(f"/tutors/course-contents/{quote_path(course_content_id)}/test", files=files, data=form_fields, params=kwargs)
        return TutorTestCreateResponse.model_validate(response.json())

    async def list_course_members(
        self,
        **kwargs: Any,
    ) -> List[TutorCourseMemberList]:
        """Tutor List Course Members Endpoint"""
        response = await self._http.get("/tutors/course-members", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [TutorCourseMemberList.model_validate(item) for item in data]
        return []

    async def get_course_members(
        self,
        course_member_id: str,
        **kwargs: Any,
    ) -> TutorCourseMemberGet:
        """Tutor Get Course Members Endpoint"""
        response = await self._http.get(f"/tutors/course-members/{quote_path(course_member_id)}", params=kwargs)
        return TutorCourseMemberGet.model_validate(response.json())

    async def list_course_members_course_contents(
        self,
        course_member_id: str,
        **kwargs: Any,
    ) -> List[CourseContentStudentList]:
        """Tutor List Course Contents Endpoint"""
        response = await self._http.get(f"/tutors/course-members/{quote_path(course_member_id)}/course-contents", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [CourseContentStudentList.model_validate(item) for item in data]
        return []

    async def get_course_members_course_contents(
        self,
        course_member_id: str,
        course_content_id: str,
        **kwargs: Any,
    ) -> CourseContentStudentGet:
        """Tutor Get Course Contents Endpoint"""
        response = await self._http.get(f"/tutors/course-members/{quote_path(course_member_id)}/course-contents/{quote_path(course_content_id)}", params=kwargs)
        return CourseContentStudentGet.model_validate(response.json())

    async def update_course_members_course_contents(
        self,
        course_member_id: str,
        course_content_id: str,
        data: Union[TutorGradeCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> TutorGradeResponse:
        """Tutor Update Course Contents Endpoint"""
        response = await self._http.patch(f"/tutors/course-members/{quote_path(course_member_id)}/course-contents/{quote_path(course_content_id)}", json_data=data, params=kwargs)
        return TutorGradeResponse.model_validate(response.json())

    async def list_courses(
        self,
        **kwargs: Any,
    ) -> List[CourseTutorList]:
        """Tutor List Courses Endpoint"""
        response = await self._http.get("/tutors/courses", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [CourseTutorList.model_validate(item) for item in data]
        return []

    async def get_courses(
        self,
        course_id: str,
        **kwargs: Any,
    ) -> CourseTutorGet:
        """Tutor Get Courses Endpoint"""
        response = await self._http.get(f"/tutors/courses/{quote_path(course_id)}", params=kwargs)
        return CourseTutorGet.model_validate(response.json())

    async def list_submission_groups(
        self,
        **kwargs: Any,
    ) -> List[TutorSubmissionGroupList]:
        """Tutor List Submission Groups Endpoint"""
        response = await self._http.get("/tutors/submission-groups", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [TutorSubmissionGroupList.model_validate(item) for item in data]
        return []

    async def get_submission_groups(
        self,
        submission_group_id: str,
        **kwargs: Any,
    ) -> TutorSubmissionGroupGet:
        """Tutor Get Submission Group Endpoint"""
        response = await self._http.get(f"/tutors/submission-groups/{quote_path(submission_group_id)}", params=kwargs)
        return TutorSubmissionGroupGet.model_validate(response.json())

    async def update_submission_groups(
        self,
        submission_group_id: str,
        data: Union[TutorSubmissionGroupLimitsUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> TutorSubmissionGroupGet:
        """Tutor Update Submission Group Limits Endpoint"""
        response = await self._http.patch(f"/tutors/submission-groups/{quote_path(submission_group_id)}", json_data=data, params=kwargs)
        return TutorSubmissionGroupGet.model_validate(response.json())

    async def get_tests(
        self,
        test_id: str,
        **kwargs: Any,
    ) -> TutorTestGet:
        """Get Tutor Test Endpoint"""
        response = await self._http.get(f"/tutors/tests/{quote_path(test_id)}", params=kwargs)
        return TutorTestGet.model_validate(response.json())

    async def get_tests_artifacts(
        self,
        test_id: str,
        **kwargs: Any,
    ) -> TutorTestArtifactList:
        """List Tutor Test Artifacts Endpoint"""
        response = await self._http.get(f"/tutors/tests/{quote_path(test_id)}/artifacts", params=kwargs)
        return TutorTestArtifactList.model_validate(response.json())

    async def get_tests_artifacts_download(
        self,
        test_id: str,
        **kwargs: Any,
    ) -> bytes:
        """Download Tutor Test Artifacts"""
        response = await self._http.get(f"/tutors/tests/{quote_path(test_id)}/artifacts/download", params=kwargs)
        return response.content

    async def tests_artifacts_upload(
        self,
        test_id: str,
        file: bytes,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Upload Tutor Test Artifacts"""
        files = {"file": file}
        response = await self._http.post(f"/tutors/tests/{quote_path(test_id)}/artifacts/upload", files=files, params=kwargs)
        return response.json()

    async def get_tests_input_download(
        self,
        test_id: str,
        **kwargs: Any,
    ) -> bytes:
        """Download Tutor Test Input"""
        response = await self._http.get(f"/tutors/tests/{quote_path(test_id)}/input/download", params=kwargs)
        return response.content

    async def tests_results(
        self,
        test_id: str,
        data: Union[TutorTestResultSubmit, Dict[str, Any]],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Submit Tutor Test Results"""
        response = await self._http.post(f"/tutors/tests/{quote_path(test_id)}/results", json_data=data, params=kwargs)
        return response.json()

    async def get_tests_status(
        self,
        test_id: str,
        **kwargs: Any,
    ) -> TutorTestStatus:
        """Get Tutor Test Status Endpoint"""
        response = await self._http.get(f"/tutors/tests/{quote_path(test_id)}/status", params=kwargs)
        return TutorTestStatus.model_validate(response.json())

