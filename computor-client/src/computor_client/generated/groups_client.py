"""Auto-generated client for /groups endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.groups import (
    GroupCreate,
    GroupGet,
    GroupList,
    GroupUpdate,
)

from computor_client.base import BaseEndpointClient


class GroupsClient(BaseEndpointClient):
    """Client for /groups endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/groups",
        )

    async def create(self, payload):
        """Create a new entity (delegates to generated POST method)."""
        return await self.post_groups(payload)

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_groups(**params)
        return await self.get_groups()

    async def update(self, id: str, payload):
        """Update entity (delegates to generated PATCH method)."""
        return await self.patch_group_by_id(id, payload)

    async def delete(self, id: str):
        """Delete entity (delegates to generated DELETE method)."""
        return await self.delete_group_by_id(id)

    async def post_groups(self, payload: GroupCreate) -> GroupGet:
        """Create Groups"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "", json=json_data)
        if data:
            return GroupGet.model_validate(data)
        return data

    async def get_groups(self, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, name: Optional[str] = None, group_type: Optional[str] = None, archived: Optional[str] = None) -> List[GroupList]:
        """List Groups"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'id', 'name', 'group_type', 'archived'] and v is not None}
        data = await self._request("GET", "", params=params)
        if isinstance(data, list):
            return [GroupList.model_validate(item) for item in data]
        return data

    async def get_group_by_id(self, id: str) -> GroupGet:
        """Get Groups"""
        data = await self._request("GET", f"/{id}")
        if data:
            return GroupGet.model_validate(data)
        return data

    async def patch_group_by_id(self, id: str, payload: GroupUpdate) -> GroupGet:
        """Update Groups"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/{id}", json=json_data)
        if data:
            return GroupGet.model_validate(data)
        return data

    async def delete_group_by_id(self, id: str) -> Any:
        """Delete Groups"""
        data = await self._request("DELETE", f"/{id}")
