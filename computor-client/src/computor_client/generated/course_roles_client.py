"""Auto-generated client for /course-roles endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.course_roles import (
    CourseRoleGet,
    CourseRoleList,
)

from computor_client.base import BaseEndpointClient


class CourseRolesClient(BaseEndpointClient):
    """Client for /course-roles endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/course-roles",
        )

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_course_roles(**params)
        return await self.get_course_roles()

    async def get(self, id: str):
        """Get entity by ID (delegates to generated GET method)."""
        return await self.get_course_role_by_id(id)

    async def get_course_role_by_id(self, id: str, user_id: Optional[str] = None) -> CourseRoleGet:
        """Get Course-Roles"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/{id}", params=params)
        if data:
            return CourseRoleGet.model_validate(data)
        return data

    async def get_course_roles(self, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, title: Optional[str] = None, description: Optional[str] = None, user_id: Optional[str] = None) -> List[CourseRoleList]:
        """List Course-Roles"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'id', 'title', 'description', 'user_id'] and v is not None}
        data = await self._request("GET", "", params=params)
        if isinstance(data, list):
            return [CourseRoleList.model_validate(item) for item in data]
        return data
