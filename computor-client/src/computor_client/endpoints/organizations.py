"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from computor_types.organizations import (
    OrganizationCreate,
    OrganizationGet,
    OrganizationList,
    OrganizationUpdate,
    OrganizationUpdateTokenUpdate,
)

from computor_client.http import AsyncHTTPClient


class OrganizationsClient:
    """
    Client for organizations endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def token(
        self,
        organization_id: str,
        data: Union[OrganizationUpdateTokenUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Patch Organizations Token"""
        response = await self._http.patch(f"/organizations/{organization_id}/token", json_data=data, params=kwargs)
        return response.json()

    async def delete(
        self,
        organization_id: str,
        **kwargs: Any,
    ) -> None:
        """Delete organization and all descendant data"""
        await self._http.delete(f"/organizations/{organization_id}", params=kwargs)
        return

    async def create(
        self,
        data: Union[OrganizationCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> OrganizationGet:
        """Create Organizations"""
        response = await self._http.post(f"/organizations", json_data=data, params=kwargs)
        return OrganizationGet.model_validate(response.json())

    async def list(
        self,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[OrganizationList]:
        """List Organizations"""
        params = query.model_dump(exclude_none=True) if query else {}
        params.update(kwargs)
        response = await self._http.get(
            f"/organizations",
            params=params,
        )
        data = response.json()
        if isinstance(data, list):
            return [OrganizationList.model_validate(item) for item in data]
        return []

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> OrganizationGet:
        """Get Organizations"""
        response = await self._http.get(f"/organizations/{id}", params=kwargs)
        return OrganizationGet.model_validate(response.json())

    async def update(
        self,
        id: str,
        data: Union[OrganizationUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> OrganizationGet:
        """Update Organizations"""
        response = await self._http.patch(f"/organizations/{id}", json_data=data, params=kwargs)
        return OrganizationGet.model_validate(response.json())

    async def delete_delete(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Organizations"""
        await self._http.delete(f"/organizations/{id}", params=kwargs)
        return

    async def archive(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Route Organizations"""
        response = await self._http.patch(f"/organizations/{id}/archive", params=kwargs)
        return

