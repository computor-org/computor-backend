"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.cascade_deletion import CascadeDeleteResult
from computor_types.organizations import (
    OrganizationCreate,
    OrganizationGet,
    OrganizationList,
    OrganizationUpdate,
    OrganizationUpdateTokenUpdate,
)
from pydantic import BaseModel

from computor_client.http import AsyncHTTPClient
from computor_client.pagination import Page
from computor_client.urls import quote_path


class OrganizationsClient:
    """
    Client for organizations endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[OrganizationList]:
        """List Organizations"""
        page = await self.list_page(skip=skip, limit=limit, query=query, **kwargs)
        return page.items

    async def list_page(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> Page[OrganizationList]:
        """List Organizations (one page, with the total row count)."""
        params = query.model_dump(mode="json", exclude_none=True) if query else {}
        params.update({"skip": skip, "limit": limit})
        params.update(kwargs)
        response = await self._http.get("/organizations", params=params)
        return Page.from_response(response, OrganizationList, skip=skip, limit=limit)

    async def create(
        self,
        data: Union[OrganizationCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> OrganizationGet:
        """Create Organizations"""
        response = await self._http.post("/organizations", json_data=data, params=kwargs)
        return OrganizationGet.model_validate(response.json())

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> OrganizationGet:
        """Get Organizations"""
        response = await self._http.get(f"/organizations/{quote_path(id)}", params=kwargs)
        return OrganizationGet.model_validate(response.json())

    async def update(
        self,
        id: str,
        data: Union[OrganizationUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> OrganizationGet:
        """Update Organizations"""
        response = await self._http.patch(f"/organizations/{quote_path(id)}", json_data=data, params=kwargs)
        return OrganizationGet.model_validate(response.json())

    async def update_archive(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Route Organizations"""
        await self._http.patch(f"/organizations/{quote_path(id)}/archive", params=kwargs)
        return

    async def update_unarchive(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Unarchive Organizations"""
        await self._http.patch(f"/organizations/{quote_path(id)}/unarchive", params=kwargs)
        return

    async def delete(
        self,
        organization_id: str,
        **kwargs: Any,
    ) -> CascadeDeleteResult:
        """Delete organization and all descendant data"""
        response = await self._http.delete(f"/organizations/{quote_path(organization_id)}", params=kwargs)
        return CascadeDeleteResult.model_validate(response.json())

    async def update_token(
        self,
        organization_id: str,
        data: Union[OrganizationUpdateTokenUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Patch Organizations Token"""
        response = await self._http.patch(f"/organizations/{quote_path(organization_id)}/token", json_data=data, params=kwargs)
        return response.json()

