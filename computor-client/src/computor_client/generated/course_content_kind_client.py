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


class CourseContentKindClient(BaseEndpointClient):
    """Client for /course-content-kinds endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/course-content-kinds",
        )

    async def create(self, payload):
        """Create a new entity (delegates to generated POST method)."""
        return await self.post_course_content_kind(payload)

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_course_content_kind(**params)
        return await self.get_course_content_kind()

    async def update(self, id: str, payload):
        """Update entity (delegates to generated PATCH method)."""
        return await self.patch_course_content_kind_by_id(id, payload)

    async def delete(self, id: str):
        """Delete entity (delegates to generated DELETE method)."""
        return await self.delete_course_content_kind_by_id(id)

    async def post_course_content_kind(self, payload: CourseContentKindCreate) -> CourseContentKindGet:
        """Create Course-Content-Kind"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "", json=json_data)
        if data:
            return CourseContentKindGet.model_validate(data)
        return data

    async def get_course_content_kind(self, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, title: Optional[str] = None, description: Optional[str] = None, has_ascendants: Optional[str] = None, has_descendants: Optional[str] = None, submittable: Optional[str] = None) -> List[CourseContentKindList]:
        """List Course-Content-Kind"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'id', 'title', 'description', 'has_ascendants', 'has_descendants', 'submittable'] and v is not None}
        data = await self._request("GET", "", params=params)
        if isinstance(data, list):
            return [CourseContentKindList.model_validate(item) for item in data]
        return data

    async def get_course_content_kind_by_id(self, id: str) -> CourseContentKindGet:
        """Get Course-Content-Kind"""
        data = await self._request("GET", f"/{id}")
        if data:
            return CourseContentKindGet.model_validate(data)
        return data

    async def patch_course_content_kind_by_id(self, id: str, payload: CourseContentKindUpdate) -> CourseContentKindGet:
        """Update Course-Content-Kind"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/{id}", json=json_data)
        if data:
            return CourseContentKindGet.model_validate(data)
        return data

    async def delete_course_content_kind_by_id(self, id: str) -> Any:
        """Delete Course-Content-Kind"""
        data = await self._request("DELETE", f"/{id}")
