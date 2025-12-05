"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.profiles import (
    ProfileCreate,
    ProfileGet,
    ProfileList,
    ProfileUpdate,
)

from computor_client.http import AsyncHTTPClient


class ProfilesClient:
    """
    Client for profiles endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        **kwargs: Any,
    ) -> List[ProfileList]:
        """List Profiles Endpoint"""
        response = await self._http.get(
            f"/profiles",
            params={"skip": skip, "limit": limit, **kwargs},
        )
        data = response.json()
        if isinstance(data, list):
            return [ProfileList.model_validate(item) for item in data]
        return []

    async def create(
        self,
        data: Union[ProfileCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> ProfileGet:
        """Create Profile Endpoint"""
        response = await self._http.post(f"/profiles", json_data=data, params=kwargs)
        return ProfileGet.model_validate(response.json())

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> ProfileGet:
        """Get Profile Endpoint"""
        response = await self._http.get(f"/profiles/{id}", params=kwargs)
        return ProfileGet.model_validate(response.json())

    async def update(
        self,
        id: str,
        data: Union[ProfileUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> ProfileGet:
        """Update Profile Endpoint"""
        response = await self._http.patch(f"/profiles/{id}", json_data=data, params=kwargs)
        return ProfileGet.model_validate(response.json())

    async def delete(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Profile Endpoint"""
        await self._http.delete(f"/profiles/{id}", params=kwargs)
        return

