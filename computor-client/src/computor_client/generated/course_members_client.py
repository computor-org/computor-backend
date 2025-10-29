"""Auto-generated client for /course-members endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.course_members import (
    CourseMemberCreate,
    CourseMemberGet,
    CourseMemberList,
    CourseMemberUpdate,
)

from computor_client.base import BaseEndpointClient


class CourseMembersClient(BaseEndpointClient):
    """Client for /course-members endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/course-members",
        )

    async def create(self, payload):
        """Create a new entity (delegates to generated POST method)."""
        return await self.post_course_members(payload)

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_course_members(**params)
        return await self.get_course_members()

    async def get(self, id: str):
        """Get entity by ID (delegates to generated GET method)."""
        return await self.get_course_member_by_id(id)

    async def update(self, id: str, payload):
        """Update entity (delegates to generated PATCH method)."""
        return await self.patch_course_member_by_id(id, payload)

    async def delete(self, id: str):
        """Delete entity (delegates to generated DELETE method)."""
        return await self.delete_course_member_by_id(id)

    async def post_course_members(self, payload: CourseMemberCreate, user_id: Optional[str] = None) -> CourseMemberGet:
        """Create Course-Members"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "", json=json_data)
        if data:
            return CourseMemberGet.model_validate(data)
        return data

    async def get_course_members(self, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, user_id: Optional[str] = None, course_id: Optional[str] = None, course_group_id: Optional[str] = None, course_role_id: Optional[str] = None, given_name: Optional[str] = None, family_name: Optional[str] = None) -> List[CourseMemberList]:
        """List Course-Members"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'id', 'user_id', 'course_id', 'course_group_id', 'course_role_id', 'given_name', 'family_name'] and v is not None}
        data = await self._request("GET", "", params=params)
        if isinstance(data, list):
            return [CourseMemberList.model_validate(item) for item in data]
        return data

    async def get_course_member_by_id(self, id: str, user_id: Optional[str] = None) -> CourseMemberGet:
        """Get Course-Members"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/{id}", params=params)
        if data:
            return CourseMemberGet.model_validate(data)
        return data

    async def patch_course_member_by_id(self, id: str, payload: CourseMemberUpdate, user_id: Optional[str] = None) -> CourseMemberGet:
        """Update Course-Members"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/{id}", json=json_data)
        if data:
            return CourseMemberGet.model_validate(data)
        return data

    async def delete_course_member_by_id(self, id: str, user_id: Optional[str] = None) -> Any:
        """Delete Course-Members"""
        data = await self._request("DELETE", f"/{id}")
