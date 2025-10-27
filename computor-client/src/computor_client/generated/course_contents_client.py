"""Auto-generated client for /course-contents endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.course_contents import (
    CourseContentCreate,
    CourseContentGet,
    CourseContentList,
    CourseContentUpdate,
)
from computor_types.deployment import (
    AssignExampleRequest,
    DeploymentSummary,
    DeploymentWithHistory,
)

from computor_client.base import BaseEndpointClient


class CourseContentsClient(BaseEndpointClient):
    """Client for /course-contents endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/course-contents",
        )

    async def create(self, payload):
        """Create a new entity (delegates to generated POST method)."""
        return await self.post_course_contents(payload)

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_course_contents(**params)
        return await self.get_course_contents()

    async def update(self, id: str, payload):
        """Update entity (delegates to generated PATCH method)."""
        return await self.patch_course_content_by_id(id, payload)

    async def delete(self, id: str):
        """Delete entity (delegates to generated DELETE method)."""
        return await self.delete_course_content_by_id(id)

    async def post_course_content_assign_example(self, content_id: str, payload: AssignExampleRequest) -> DeploymentWithHistory:
        """Assign Example To Content"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", f"/{content_id}/assign-example", json=json_data)
        if data:
            return DeploymentWithHistory.model_validate(data)
        return data

    async def delete_course_content_example(self, content_id: str) -> Dict[str, Any]:
        """Unassign Example From Content"""
        data = await self._request("DELETE", f"/{content_id}/example")
        if data:
            return Dict[str, Any].model_validate(data)
        return data

    async def get_course_content_deployment_by_content_id(self, content_id: str) -> Dict[str, Any]:
        """Get Deployment Status With Workflow"""
        data = await self._request("GET", f"/deployment/{content_id}")
        if data:
            return Dict[str, Any].model_validate(data)
        return data

    async def get_course_content_cours_deployment_summary(self, course_id: str) -> DeploymentSummary:
        """Get Course Deployment Summary"""
        data = await self._request("GET", f"/courses/{course_id}/deployment-summary")
        if data:
            return DeploymentSummary.model_validate(data)
        return data

    async def get_course_content_deployment(self, content_id: str) -> Dict[str, Any]:
        """Get Content Deployment"""
        data = await self._request("GET", f"/{content_id}/deployment")
        if data:
            return Dict[str, Any].model_validate(data)
        return data

    async def post_course_contents(self, payload: CourseContentCreate) -> CourseContentGet:
        """Create Course-Contents"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "", json=json_data)
        if data:
            return CourseContentGet.model_validate(data)
        return data

    async def get_course_contents(self, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, title: Optional[str] = None, description: Optional[str] = None, path: Optional[str] = None, course_id: Optional[str] = None, course_content_type_id: Optional[str] = None, archived: Optional[str] = None, position: Optional[str] = None, max_group_size: Optional[str] = None, max_test_runs: Optional[str] = None, max_submissions: Optional[str] = None, execution_backend_id: Optional[str] = None, example_version_id: Optional[str] = None, has_deployment: Optional[str] = None) -> List[CourseContentList]:
        """List Course-Contents"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'id', 'title', 'description', 'path', 'course_id', 'course_content_type_id', 'archived', 'position', 'max_group_size', 'max_test_runs', 'max_submissions', 'execution_backend_id', 'example_version_id', 'has_deployment'] and v is not None}
        data = await self._request("GET", "", params=params)
        if isinstance(data, list):
            return [CourseContentList.model_validate(item) for item in data]
        return data

    async def get_course_content_by_id(self, id: str) -> CourseContentGet:
        """Get Course-Contents"""
        data = await self._request("GET", f"/{id}")
        if data:
            return CourseContentGet.model_validate(data)
        return data

    async def patch_course_content_by_id(self, id: str, payload: CourseContentUpdate) -> CourseContentGet:
        """Update Course-Contents"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/{id}", json=json_data)
        if data:
            return CourseContentGet.model_validate(data)
        return data

    async def delete_course_content_by_id(self, id: str) -> Any:
        """Delete Course-Contents"""
        data = await self._request("DELETE", f"/{id}")

    async def patch_course_content_by_id_archive(self, id: str) -> Any:
        """Route Course-Contents"""
        data = await self._request("PATCH", f"/{id}/archive")
