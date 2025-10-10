"""Auto-generated client for /courses endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.course_execution_backends import CourseExecutionBackendGet
from computor_types.courses import (
    CourseCreate,
    CourseGet,
    CourseList,
    CourseUpdate,
)

from computor_client.base import BaseEndpointClient


class CoursesClient(BaseEndpointClient):
    """Client for /courses endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/courses",
        )

    async def create(self, payload):
        """Create a new entity (delegates to generated POST method)."""
        return await self.post_courses(payload)

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_courses(**params)
        return await self.get_courses()

    async def update(self, id: str, payload):
        """Update entity (delegates to generated PATCH method)."""
        return await self.patch_cours_by_id(id, payload)

    async def delete(self, id: str):
        """Delete entity (delegates to generated DELETE method)."""
        return await self.delete_cours_by_id(id)

    async def patch_cours_execution_backend_by_execution_backend_id(self, course_id: str, execution_backend_id: str) -> CourseExecutionBackendGet:
        """Patch Course Execution Backend Endpoint"""
        data = await self._request("PATCH", f"/{course_id}/execution-backends/{execution_backend_id}")
        if data:
            return CourseExecutionBackendGet.model_validate(data)
        return data

    async def delete_cours_execution_backend_by_execution_backend_id(self, course_id: str, execution_backend_id: str) -> Dict[str, Any]:
        """Delete Course Execution Backend Endpoint"""
        data = await self._request("DELETE", f"/{course_id}/execution-backends/{execution_backend_id}")
        if data:
            return Dict[str, Any].model_validate(data)
        return data

    async def post_courses(self, payload: CourseCreate) -> CourseGet:
        """Create Courses"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "", json=json_data)
        if data:
            return CourseGet.model_validate(data)
        return data

    async def get_courses(self, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, title: Optional[str] = None, description: Optional[str] = None, path: Optional[str] = None, course_family_id: Optional[str] = None, organization_id: Optional[str] = None, language_code: Optional[str] = None, provider_url: Optional[str] = None, full_path: Optional[str] = None) -> List[CourseList]:
        """List Courses"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'id', 'title', 'description', 'path', 'course_family_id', 'organization_id', 'language_code', 'provider_url', 'full_path'] and v is not None}
        data = await self._request("GET", "", params=params)
        if isinstance(data, list):
            return [CourseList.model_validate(item) for item in data]
        return data

    async def get_cours_by_id(self, id: str) -> CourseGet:
        """Get Courses"""
        data = await self._request("GET", f"/{id}")
        if data:
            return CourseGet.model_validate(data)
        return data

    async def patch_cours_by_id(self, id: str, payload: CourseUpdate) -> CourseGet:
        """Update Courses"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/{id}", json=json_data)
        if data:
            return CourseGet.model_validate(data)
        return data

    async def delete_cours_by_id(self, id: str) -> Any:
        """Delete Courses"""
        data = await self._request("DELETE", f"/{id}")
