"""Auto-generated client for /course-families endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.course_families import (
    CourseFamilyCreate,
    CourseFamilyGet,
    CourseFamilyList,
    CourseFamilyUpdate,
)

from computor_client.base import BaseEndpointClient


class CourseFamiliesClient(BaseEndpointClient):
    """Client for /course-families endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/course-families",
        )

    async def create(self, payload):
        """Create a new entity (delegates to generated POST method)."""
        return await self.post_course_families(payload)

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_course_families(**params)
        return await self.get_course_families()

    async def get(self, id: str):
        """Get entity by ID (delegates to generated GET method)."""
        return await self.get_course_family_by_id(id)

    async def update(self, id: str, payload):
        """Update entity (delegates to generated PATCH method)."""
        return await self.patch_course_family_by_id(id, payload)

    async def delete(self, id: str):
        """Delete entity (delegates to generated DELETE method)."""
        return await self.delete_course_family_by_id(id)

    async def post_course_families(self, payload: CourseFamilyCreate, user_id: Optional[str] = None) -> CourseFamilyGet:
        """Create Course-Families"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "", json=json_data)
        if data:
            return CourseFamilyGet.model_validate(data)
        return data

    async def get_course_families(self, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, title: Optional[str] = None, description: Optional[str] = None, path: Optional[str] = None, organization_id: Optional[str] = None, user_id: Optional[str] = None) -> List[CourseFamilyList]:
        """List Course-Families"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'id', 'title', 'description', 'path', 'organization_id', 'user_id'] and v is not None}
        data = await self._request("GET", "", params=params)
        if isinstance(data, list):
            return [CourseFamilyList.model_validate(item) for item in data]
        return data

    async def get_course_family_by_id(self, id: str, user_id: Optional[str] = None) -> CourseFamilyGet:
        """Get Course-Families"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/{id}", params=params)
        if data:
            return CourseFamilyGet.model_validate(data)
        return data

    async def patch_course_family_by_id(self, id: str, payload: CourseFamilyUpdate, user_id: Optional[str] = None) -> CourseFamilyGet:
        """Update Course-Families"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/{id}", json=json_data)
        if data:
            return CourseFamilyGet.model_validate(data)
        return data

    async def delete_course_family_by_id(self, id: str, user_id: Optional[str] = None) -> Any:
        """Delete Course-Families"""
        data = await self._request("DELETE", f"/{id}")
