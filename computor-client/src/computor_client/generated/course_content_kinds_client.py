"""Auto-generated client for /course-content-kinds endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.course_content_kind import (
    CourseContentKindCreate,
    CourseContentKindGet,
    CourseContentKindList,
    CourseContentKindUpdate,
)

from computor_client.base import BaseEndpointClient


class CourseContentKindsClient(BaseEndpointClient):
    """Client for /course-content-kinds endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/course-content-kinds",
        )

    async def create(self, payload):
        """Create a new entity (delegates to generated POST method)."""
        return await self.post_course_content_kinds(payload)

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_course_content_kinds(**params)
        return await self.get_course_content_kinds()

    async def get(self, id: str):
        """Get entity by ID (delegates to generated GET method)."""
        return await self.get_course_content_kind_by_id(id)

    async def update(self, id: str, payload):
        """Update entity (delegates to generated PATCH method)."""
        return await self.patch_course_content_kind_by_id(id, payload)

    async def delete(self, id: str):
        """Delete entity (delegates to generated DELETE method)."""
        return await self.delete_course_content_kind_by_id(id)

    async def post_course_content_kinds(self, payload: CourseContentKindCreate, user_id: Optional[str] = None) -> CourseContentKindGet:
        """Create Course-Content-Kinds"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "", json=json_data)
        if data:
            return CourseContentKindGet.model_validate(data)
        return data

    async def get_course_content_kinds(self, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, title: Optional[str] = None, description: Optional[str] = None, has_ascendants: Optional[str] = None, has_descendants: Optional[str] = None, submittable: Optional[str] = None, user_id: Optional[str] = None) -> List[CourseContentKindList]:
        """List Course-Content-Kinds"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'id', 'title', 'description', 'has_ascendants', 'has_descendants', 'submittable', 'user_id'] and v is not None}
        data = await self._request("GET", "", params=params)
        if isinstance(data, list):
            return [CourseContentKindList.model_validate(item) for item in data]
        return data

    async def get_course_content_kind_by_id(self, id: str, user_id: Optional[str] = None) -> CourseContentKindGet:
        """Get Course-Content-Kinds"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/{id}", params=params)
        if data:
            return CourseContentKindGet.model_validate(data)
        return data

    async def patch_course_content_kind_by_id(self, id: str, payload: CourseContentKindUpdate, user_id: Optional[str] = None) -> CourseContentKindGet:
        """Update Course-Content-Kinds"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/{id}", json=json_data)
        if data:
            return CourseContentKindGet.model_validate(data)
        return data

    async def delete_course_content_kind_by_id(self, id: str, user_id: Optional[str] = None) -> Any:
        """Delete Course-Content-Kinds"""
        data = await self._request("DELETE", f"/{id}")
