"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from computor_types.profiles import (
    ProfileCreate,
    ProfileGet,
    ProfileList,
    ProfileUpdate,
)

from computor_client.http import AsyncHTTPClient
from computor_client.pagination import Page
from computor_client.urls import quote_path


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
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[ProfileList]:
        """List Profiles Endpoint"""
        page = await self.list_page(skip=skip, limit=limit, query=query, **kwargs)
        return page.items

    async def list_page(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> Page[ProfileList]:
        """List Profiles Endpoint (one page, with the total row count)."""
        params = query.model_dump(mode="json", exclude_none=True) if query else {}
        params.update({"skip": skip, "limit": limit})
        params.update(kwargs)
        response = await self._http.get(f"/profiles", params=params)
        return Page.from_response(response, ProfileList, skip=skip, limit=limit)

    async def create(
        self,
        data: Union[ProfileCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> ProfileGet:
        """Create Profile Endpoint"""
        response = await self._http.post(f"/profiles", json_data=data, params=kwargs)
        return ProfileGet.model_validate(response.json())

    async def delete(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Profile Endpoint"""
        await self._http.delete(f"/profiles/{quote_path(id)}", params=kwargs)
        return

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> ProfileGet:
        """Get Profile Endpoint"""
        response = await self._http.get(f"/profiles/{quote_path(id)}", params=kwargs)
        return ProfileGet.model_validate(response.json())

    async def update(
        self,
        id: str,
        data: Union[ProfileUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> ProfileGet:
        """Update Profile Endpoint"""
        response = await self._http.patch(f"/profiles/{quote_path(id)}", json_data=data, params=kwargs)
        return ProfileGet.model_validate(response.json())

