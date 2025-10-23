"""Auto-generated client for /users endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.users import (
    UserCreate,
    UserGet,
    UserList,
    UserUpdate,
)

from computor_client.base import BaseEndpointClient


class UsersClient(BaseEndpointClient):
    """Client for /users endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/users",
        )

    async def create(self, payload):
        """Create a new entity (delegates to generated POST method)."""
        return await self.post_users(payload)

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_users(**params)
        return await self.get_users()

    async def update(self, id: str, payload):
        """Update entity (delegates to generated PATCH method)."""
        return await self.patch_user_by_id_archive(id, payload)

    async def delete(self, id: str):
        """Delete entity (delegates to generated DELETE method)."""
        return await self.delete_user_by_id(id)

    async def post_users(self, payload: UserCreate) -> UserGet:
        """Create Users"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "", json=json_data)
        if data:
            return UserGet.model_validate(data)
        return data

    async def get_users(self, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, given_name: Optional[str] = None, family_name: Optional[str] = None, email: Optional[str] = None, number: Optional[str] = None, user_type: Optional[str] = None, archived: Optional[str] = None, username: Optional[str] = None) -> List[UserList]:
        """List Users"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'id', 'given_name', 'family_name', 'email', 'number', 'user_type', 'archived', 'username'] and v is not None}
        data = await self._request("GET", "", params=params)
        if isinstance(data, list):
            return [UserList.model_validate(item) for item in data]
        return data

    async def get_user_by_id(self, id: str) -> UserGet:
        """Get Users"""
        data = await self._request("GET", f"/{id}")
        if data:
            return UserGet.model_validate(data)
        return data

    async def patch_user_by_id(self, id: str, payload: UserUpdate) -> UserGet:
        """Update Users"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/{id}", json=json_data)
        if data:
            return UserGet.model_validate(data)
        return data

    async def delete_user_by_id(self, id: str) -> Any:
        """Delete Users"""
        data = await self._request("DELETE", f"/{id}")

    async def patch_user_by_id_archive(self, id: str) -> Any:
        """Route Users"""
        data = await self._request("PATCH", f"/{id}/archive")
