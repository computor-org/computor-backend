"""Auto-generated client for /system endpoints."""

from typing import Optional, List, Dict, Any
import httpx

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

from computor_client.base import BaseEndpointClient


class SystemClient(BaseEndpointClient):
    """Client for /system endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/system",
        )

    async def post_system_deploy_organizations(self, payload: OrganizationTaskRequest, user_id: Optional[str] = None) -> TaskResponse:
        """Create Organization Async"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "/deploy/organizations", json=json_data)
        if data:
            return TaskResponse.model_validate(data)
        return data

    async def post_system_deploy_course_families(self, payload: CourseFamilyTaskRequest, user_id: Optional[str] = None) -> TaskResponse:
        """Create Course Family Async"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "/deploy/course-families", json=json_data)
        if data:
            return TaskResponse.model_validate(data)
        return data

    async def post_system_deploy_courses(self, payload: CourseTaskRequest, user_id: Optional[str] = None) -> TaskResponse:
        """Create Course Async"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "/deploy/courses", json=json_data)
        if data:
            return TaskResponse.model_validate(data)
        return data

    async def post_system_cours_generate_student_template(self, course_id: str, payload: GenerateTemplateRequest, user_id: Optional[str] = None) -> GenerateTemplateResponse:
        """Generate Student Template"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", f"/courses/{course_id}/generate-student-template", json=json_data)
        if data:
            return GenerateTemplateResponse.model_validate(data)
        return data

    async def post_system_cours_generate_assignment(self, course_id: str, payload: GenerateAssignmentsRequest, user_id: Optional[str] = None) -> GenerateAssignmentsResponse:
        """Generate Assignments"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", f"/courses/{course_id}/generate-assignments", json=json_data)
        if data:
            return GenerateAssignmentsResponse.model_validate(data)
        return data

    async def get_system_cours_gitlab_statu(self, course_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get Course Gitlab Status"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/courses/{course_id}/gitlab-status", params=params)
        if data:
            return Dict[str, Any].model_validate(data)
        return data

    async def post_system_hierarchy_create(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Create Hierarchy"""
        data = await self._request("POST", "/hierarchy/create")
        if data:
            return Dict[str, Any].model_validate(data)
        return data

    async def get_system_hierarchy_statu_by_workflow_id(self, workflow_id: str) -> Dict[str, Any]:
        """Get Hierarchy Status"""
        data = await self._request("GET", f"/hierarchy/status/{workflow_id}")
        if data:
            return Dict[str, Any].model_validate(data)
        return data
