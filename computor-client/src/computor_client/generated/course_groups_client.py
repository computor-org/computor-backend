"""Auto-generated client for /course-groups endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.course_groups import (
    CourseGroupCreate,
    CourseGroupGet,
    CourseGroupList,
    CourseGroupUpdate,
)

from computor_client.base import BaseEndpointClient


class CourseGroupsClient(BaseEndpointClient):
    """Client for /course-groups endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/course-groups",
        )

    async def create(self, payload):
        """Create a new entity (delegates to generated POST method)."""
        return await self.post_course_groups(payload)

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_course_groups(**params)
        return await self.get_course_groups()

    async def update(self, id: str, payload):
        """Update entity (delegates to generated PATCH method)."""
        return await self.patch_course_group_by_id(id, payload)

    async def delete(self, id: str):
        """Delete entity (delegates to generated DELETE method)."""
        return await self.delete_course_group_by_id(id)

    async def post_course_groups(self, payload: CourseGroupCreate) -> CourseGroupGet:
        """Create Course-Groups"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "", json=json_data)
        if data:
            return CourseGroupGet.model_validate(data)
        return data

    async def get_course_groups(self, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, title: Optional[str] = None, course_id: Optional[str] = None) -> List[CourseGroupList]:
        """List Course-Groups"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'id', 'title', 'course_id'] and v is not None}
        data = await self._request("GET", "", params=params)
        if isinstance(data, list):
            return [CourseGroupList.model_validate(item) for item in data]
        return data

    async def get_course_group_by_id(self, id: str) -> CourseGroupGet:
        """Get Course-Groups"""
        data = await self._request("GET", f"/{id}")
        if data:
            return CourseGroupGet.model_validate(data)
        return data

    async def patch_course_group_by_id(self, id: str, payload: CourseGroupUpdate) -> CourseGroupGet:
        """Update Course-Groups"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/{id}", json=json_data)
        if data:
            return CourseGroupGet.model_validate(data)
        return data

    async def delete_course_group_by_id(self, id: str) -> Any:
        """Delete Course-Groups"""
        data = await self._request("DELETE", f"/{id}")
