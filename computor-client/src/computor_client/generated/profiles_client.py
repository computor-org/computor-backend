"""Auto-generated client for /profiles endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.profiles import (
    ProfileCreate,
    ProfileGet,
    ProfileList,
    ProfileUpdate,
)

from computor_client.base import BaseEndpointClient


class ProfilesClient(BaseEndpointClient):
    """Client for /profiles endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/profiles",
        )

    async def create(self, payload):
        """Create a new entity (delegates to generated POST method)."""
        return await self.post_profiles(payload)

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_profiles(**params)
        return await self.get_profiles()

    async def get(self, id: str):
        """Get entity by ID (delegates to generated GET method)."""
        return await self.get_profile_by_id(id)

    async def update(self, id: str, payload):
        """Update entity (delegates to generated PATCH method)."""
        return await self.patch_profile_by_id(id, payload)

    async def delete(self, id: str):
        """Delete entity (delegates to generated DELETE method)."""
        return await self.delete_profile_by_id(id)

    async def get_profiles(self, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, user_id: Optional[str] = None, nickname: Optional[str] = None) -> List[ProfileList]:
        """List Profiles Endpoint"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'id', 'user_id', 'nickname'] and v is not None}
        data = await self._request("GET", "", params=params)
        if isinstance(data, list):
            return [ProfileList.model_validate(item) for item in data]
        return data

    async def post_profiles(self, payload: ProfileCreate, user_id: Optional[str] = None) -> ProfileGet:
        """Create Profile Endpoint"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "", json=json_data)
        if data:
            return ProfileGet.model_validate(data)
        return data

    async def get_profile_by_id(self, id: str, user_id: Optional[str] = None) -> ProfileGet:
        """Get Profile Endpoint"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/{id}", params=params)
        if data:
            return ProfileGet.model_validate(data)
        return data

    async def patch_profile_by_id(self, id: str, payload: ProfileUpdate, user_id: Optional[str] = None) -> ProfileGet:
        """Update Profile Endpoint"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/{id}", json=json_data)
        if data:
            return ProfileGet.model_validate(data)
        return data

    async def delete_profile_by_id(self, id: str, user_id: Optional[str] = None) -> Any:
        """Delete Profile Endpoint"""
        data = await self._request("DELETE", f"/{id}")
