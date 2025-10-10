"""Auto-generated client for /user-roles endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.user_roles import (
    UserRoleCreate,
    UserRoleGet,
    UserRoleList,
)

from computor_client.base import BaseEndpointClient


class UserRolesClient(BaseEndpointClient):
    """Client for /user-roles endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/user-roles",
        )

    async def create(self, payload):
        """Create a new entity (delegates to generated POST method)."""
        return await self.post_user_roles(payload)

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_user_roles(**params)
        return await self.get_user_roles()

    async def delete(self, id: str):
        """Delete entity (delegates to generated DELETE method)."""
        return await self.delete_user_role_user_role_by_role_id(id)

    async def get_user_roles(self, skip: Optional[str] = None, limit: Optional[str] = None, user_id: Optional[str] = None, role_id: Optional[str] = None) -> List[UserRoleList]:
        """List User Roles"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'user_id', 'role_id'] and v is not None}
        data = await self._request("GET", "", params=params)
        if isinstance(data, list):
            return [UserRoleList.model_validate(item) for item in data]
        return data

    async def post_user_roles(self, payload: UserRoleCreate) -> UserRoleGet:
        """Create User Role"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "", json=json_data)
        if data:
            return UserRoleGet.model_validate(data)
        return data

    async def get_user_role_user_role_by_role_id(self, user_id: str, role_id: str) -> UserRoleGet:
        """Get User Role Endpoint"""
        data = await self._request("GET", f"/users/{user_id}/roles/{role_id}")
        if data:
            return UserRoleGet.model_validate(data)
        return data

    async def delete_user_role_user_role_by_role_id(self, user_id: str, role_id: str) -> Dict[str, Any]:
        """Delete User Role Endpoint"""
        data = await self._request("DELETE", f"/users/{user_id}/roles/{role_id}")
        if data:
            return Dict[str, Any].model_validate(data)
        return data
