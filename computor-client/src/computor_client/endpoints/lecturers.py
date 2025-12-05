"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.courses import (
    CourseGet,
    CourseList,
)
from computor_types.lecturer_content_validation import (
    ContentValidationCreate,
    ContentValidationGet,
)
from computor_types.lecturer_course_contents import (
    CourseContentLecturerGet,
    CourseContentLecturerList,
)
from computor_types.lecturer_deployments import (
    AssignExampleResponse,
    DeploymentGet,
    UnassignExampleResponse,
)
from computor_types.lecturer_gitlab_sync import (
    GitLabSyncRequest,
    GitLabSyncResult,
)

from computor_client.http import AsyncHTTPClient


class LecturersClient:
    """
    Client for lecturers endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def courses(
        self,
        course_id: str,
        **kwargs: Any,
    ) -> CourseGet:
        """Lecturer Get Courses Endpoint"""
        response = await self._http.get(f"/lecturers/courses/{course_id}", params=kwargs)
        return CourseGet.model_validate(response.json())

    async def get_courses(
        self,
        **kwargs: Any,
    ) -> List[CourseList]:
        """Lecturer List Courses Endpoint"""
        response = await self._http.get(f"/lecturers/courses", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [CourseList.model_validate(item) for item in data]
        return []

    async def course_contents(
        self,
        course_content_id: str,
        **kwargs: Any,
    ) -> CourseContentLecturerGet:
        """Lecturer Get Course Contents Endpoint"""
        response = await self._http.get(f"/lecturers/course-contents/{course_content_id}", params=kwargs)
        return CourseContentLecturerGet.model_validate(response.json())

    async def get_course_contents(
        self,
        **kwargs: Any,
    ) -> List[CourseContentLecturerList]:
        """Lecturer List Course Contents Endpoint"""
        response = await self._http.get(f"/lecturers/course-contents", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [CourseContentLecturerList.model_validate(item) for item in data]
        return []

    async def course_contents_assign_example(
        self,
        course_content_id: str,
        **kwargs: Any,
    ) -> AssignExampleResponse:
        """Assign Example To Course Content"""
        response = await self._http.post(f"/lecturers/course-contents/{course_content_id}/assign-example", params=kwargs)
        return AssignExampleResponse.model_validate(response.json())

    async def course_contents_deployment(
        self,
        course_content_id: str,
        **kwargs: Any,
    ) -> DeploymentGet:
        """Get Course Content Deployment"""
        response = await self._http.get(f"/lecturers/course-contents/{course_content_id}/deployment", params=kwargs)
        return DeploymentGet.model_validate(response.json())

    async def delete_course_contents_deployment(
        self,
        course_content_id: str,
        **kwargs: Any,
    ) -> UnassignExampleResponse:
        """Unassign Example From Course Content"""
        await self._http.delete(f"/lecturers/course-contents/{course_content_id}/deployment", params=kwargs)
        return

    async def courses_validate(
        self,
        course_id: str,
        data: Union[ContentValidationCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> ContentValidationGet:
        """Validate Course Content Batch"""
        response = await self._http.post(f"/lecturers/courses/{course_id}/validate", json_data=data, params=kwargs)
        return ContentValidationGet.model_validate(response.json())

    async def course_members_sync_gitlab(
        self,
        course_member_id: str,
        data: Union[GitLabSyncRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> GitLabSyncResult:
        """Sync Member Gitlab Permissions Endpoint"""
        response = await self._http.post(f"/lecturers/course-members/{course_member_id}/sync-gitlab", json_data=data, params=kwargs)
        return GitLabSyncResult.model_validate(response.json())

