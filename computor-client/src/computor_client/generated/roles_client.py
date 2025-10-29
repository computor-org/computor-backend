"""Auto-generated client for /roles endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.roles import (
    RoleGet,
    RoleList,
)

from computor_client.base import BaseEndpointClient


class RolesClient(BaseEndpointClient):
    """Client for /roles endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/roles",
        )

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_roles(**params)
        return await self.get_roles()

    async def get(self, id: str):
        """Get entity by ID (delegates to generated GET method)."""
        return await self.get_role_by_id(id)

    async def get_role_by_id(self, id: str, user_id: Optional[str] = None) -> RoleGet:
        """Get Roles"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/{id}", params=params)
        if data:
            return RoleGet.model_validate(data)
        return data

    async def get_roles(self, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, title: Optional[str] = None, description: Optional[str] = None, builtin: Optional[str] = None, user_id: Optional[str] = None) -> List[RoleList]:
        """List Roles"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'id', 'title', 'description', 'builtin', 'user_id'] and v is not None}
        data = await self._request("GET", "", params=params)
        if isinstance(data, list):
            return [RoleList.model_validate(item) for item in data]
        return data
