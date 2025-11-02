"""Auto-generated client for /lecturers endpoints."""

from typing import Optional, List, Dict, Any
import httpx

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
    AssignExampleRequest,
    AssignExampleResponse,
    DeploymentGet,
    UnassignExampleResponse,
)

from computor_client.base import RoleBasedViewClient


class LecturersClient(RoleBasedViewClient):
    """Client for /lecturers endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/lecturers",
        )

    async def get_lecturer_cours_by_course_id(self, course_id: str, user_id: Optional[str] = None) -> CourseGet:
        """Lecturer Get Courses Endpoint"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/courses/{course_id}", params=params)
        if data:
            return CourseGet.model_validate(data)
        return data

    async def get_lecturers_courses(self, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, title: Optional[str] = None, description: Optional[str] = None, path: Optional[str] = None, course_family_id: Optional[str] = None, organization_id: Optional[str] = None, language_code: Optional[str] = None, provider_url: Optional[str] = None, full_path: Optional[str] = None, user_id: Optional[str] = None) -> List[CourseList]:
        """Lecturer List Courses Endpoint"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'id', 'title', 'description', 'path', 'course_family_id', 'organization_id', 'language_code', 'provider_url', 'full_path', 'user_id'] and v is not None}
        data = await self._request("GET", "/courses", params=params)
        if isinstance(data, list):
            return [CourseList.model_validate(item) for item in data]
        return data

    async def get_lecturer_course_content_by_course_content_id(self, course_content_id: str, user_id: Optional[str] = None) -> CourseContentLecturerGet:
        """Lecturer Get Course Contents Endpoint"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/course-contents/{course_content_id}", params=params)
        if data:
            return CourseContentLecturerGet.model_validate(data)
        return data

    async def get_lecturers_course_contents(self, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, title: Optional[str] = None, path: Optional[str] = None, course_id: Optional[str] = None, course_content_type_id: Optional[str] = None, archived: Optional[str] = None, position: Optional[str] = None, max_group_size: Optional[str] = None, max_test_runs: Optional[str] = None, max_submissions: Optional[str] = None, execution_backend_id: Optional[str] = None, has_deployment: Optional[str] = None, directory: Optional[str] = None, project: Optional[str] = None, provider_url: Optional[str] = None, nlevel: Optional[str] = None, descendants: Optional[str] = None, ascendants: Optional[str] = None, user_id: Optional[str] = None) -> List[CourseContentLecturerList]:
        """Lecturer List Course Contents Endpoint"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'id', 'title', 'path', 'course_id', 'course_content_type_id', 'archived', 'position', 'max_group_size', 'max_test_runs', 'max_submissions', 'execution_backend_id', 'has_deployment', 'directory', 'project', 'provider_url', 'nlevel', 'descendants', 'ascendants', 'user_id'] and v is not None}
        data = await self._request("GET", "/course-contents", params=params)
        if isinstance(data, list):
            return [CourseContentLecturerList.model_validate(item) for item in data]
        return data

    async def post_lecturer_course_content_assign_example(self, course_content_id: str, payload: AssignExampleRequest, user_id: Optional[str] = None) -> AssignExampleResponse:
        """Assign Example To Course Content"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", f"/course-contents/{course_content_id}/assign-example", json=json_data)
        if data:
            return AssignExampleResponse.model_validate(data)
        return data

    async def get_lecturer_course_content_deployment(self, course_content_id: str, user_id: Optional[str] = None) -> DeploymentGet:
        """Get Course Content Deployment"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/course-contents/{course_content_id}/deployment", params=params)
        if data:
            return DeploymentGet.model_validate(data)
        return data

    async def delete_lecturer_course_content_deployment(self, course_content_id: str, user_id: Optional[str] = None) -> UnassignExampleResponse:
        """Unassign Example From Course Content"""
        data = await self._request("DELETE", f"/course-contents/{course_content_id}/deployment")
        if data:
            return UnassignExampleResponse.model_validate(data)
        return data

    async def post_lecturer_cours_validate(self, course_id: str, payload: ContentValidationCreate, user_id: Optional[str] = None) -> ContentValidationGet:
        """Validate Course Content Batch"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", f"/courses/{course_id}/validate", json=json_data)
        if data:
            return ContentValidationGet.model_validate(data)
        return data
