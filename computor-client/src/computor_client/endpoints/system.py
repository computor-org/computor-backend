"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from computor_types.system import (
    CourseFamilyTaskRequest,
    CourseTaskRequest,
    GenerateAssignmentsRequest,
    GenerateAssignmentsResponse,
    GenerateTemplateRequest,
    GenerateTemplateResponse,
    OrganizationTaskRequest,
    TaskResponse,
)

from computor_client.http import AsyncHTTPClient


class SystemClient:
    """
    Client for system endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def deploy_organizations(
        self,
        data: Union[OrganizationTaskRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> TaskResponse:
        """Create Organization Async"""
        response = await self._http.post(f"/system/deploy/organizations", json_data=data, params=kwargs)
        return TaskResponse.model_validate(response.json())

    async def deploy_course_families(
        self,
        data: Union[CourseFamilyTaskRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> TaskResponse:
        """Create Course Family Async"""
        response = await self._http.post(f"/system/deploy/course-families", json_data=data, params=kwargs)
        return TaskResponse.model_validate(response.json())

    async def deploy_courses(
        self,
        data: Union[CourseTaskRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> TaskResponse:
        """Create Course Async"""
        response = await self._http.post(f"/system/deploy/courses", json_data=data, params=kwargs)
        return TaskResponse.model_validate(response.json())

    async def courses_generate_student_template(
        self,
        course_id: str,
        data: Union[GenerateTemplateRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> GenerateTemplateResponse:
        """Generate Student Template"""
        response = await self._http.post(f"/system/courses/{course_id}/generate-student-template", json_data=data, params=kwargs)
        return GenerateTemplateResponse.model_validate(response.json())

    async def courses_generate_assignments(
        self,
        course_id: str,
        data: Union[GenerateAssignmentsRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> GenerateAssignmentsResponse:
        """Generate Assignments"""
        response = await self._http.post(f"/system/courses/{course_id}/generate-assignments", json_data=data, params=kwargs)
        return GenerateAssignmentsResponse.model_validate(response.json())

    async def course_families_sync_documents(
        self,
        course_family_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Sync Documents Repository"""
        response = await self._http.post(f"/system/course-families/{course_family_id}/sync-documents", params=kwargs)
        return response.json()

    async def courses_gitlab_status(
        self,
        course_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Course Gitlab Status"""
        response = await self._http.get(f"/system/courses/{course_id}/gitlab-status", params=kwargs)
        return response.json()

    async def hierarchy_create(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Create Hierarchy"""
        response = await self._http.post(f"/system/hierarchy/create", params=kwargs)
        return response.json()

    async def hierarchy_status(
        self,
        workflow_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Hierarchy Status"""
        response = await self._http.get(f"/system/hierarchy/status/{workflow_id}", params=kwargs)
        return response.json()

