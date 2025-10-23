"""Auto-generated client for /course-content-types endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.course_content_types import (
    CourseContentTypeCreate,
    CourseContentTypeGet,
    CourseContentTypeList,
    CourseContentTypeUpdate,
)

from computor_client.base import BaseEndpointClient


class CourseContentTypesClient(BaseEndpointClient):
    """Client for /course-content-types endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/course-content-types",
        )

    async def create(self, payload):
        """Create a new entity (delegates to generated POST method)."""
        return await self.post_course_content_types(payload)

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_course_content_types(**params)
        return await self.get_course_content_types()

    async def update(self, id: str, payload):
        """Update entity (delegates to generated PATCH method)."""
        return await self.patch_course_content_type_by_id(id, payload)

    async def delete(self, id: str):
        """Delete entity (delegates to generated DELETE method)."""
        return await self.delete_course_content_type_by_id(id)

    async def post_course_content_types(self, payload: CourseContentTypeCreate) -> CourseContentTypeGet:
        """Create Course-Content-Types"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "", json=json_data)
        if data:
            return CourseContentTypeGet.model_validate(data)
        return data

    async def get_course_content_types(self, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, slug: Optional[str] = None, title: Optional[str] = None, color: Optional[str] = None, description: Optional[str] = None, course_id: Optional[str] = None, course_content_kind_id: Optional[str] = None) -> List[CourseContentTypeList]:
        """List Course-Content-Types"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'id', 'slug', 'title', 'color', 'description', 'course_id', 'course_content_kind_id'] and v is not None}
        data = await self._request("GET", "", params=params)
        if isinstance(data, list):
            return [CourseContentTypeList.model_validate(item) for item in data]
        return data

    async def get_course_content_type_by_id(self, id: str) -> CourseContentTypeGet:
        """Get Course-Content-Types"""
        data = await self._request("GET", f"/{id}")
        if data:
            return CourseContentTypeGet.model_validate(data)
        return data

    async def patch_course_content_type_by_id(self, id: str, payload: CourseContentTypeUpdate) -> CourseContentTypeGet:
        """Update Course-Content-Types"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/{id}", json=json_data)
        if data:
            return CourseContentTypeGet.model_validate(data)
        return data

    async def delete_course_content_type_by_id(self, id: str) -> Any:
        """Delete Course-Content-Types"""
        data = await self._request("DELETE", f"/{id}")
