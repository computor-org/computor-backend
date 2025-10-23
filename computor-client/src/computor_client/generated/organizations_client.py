"""Auto-generated client for /organizations endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.organizations import (
    OrganizationCreate,
    OrganizationGet,
    OrganizationList,
    OrganizationUpdate,
    OrganizationUpdateTokenUpdate,
)

from computor_client.base import BaseEndpointClient


class OrganizationsClient(BaseEndpointClient):
    """Client for /organizations endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/organizations",
        )

    async def create(self, payload):
        """Create a new entity (delegates to generated POST method)."""
        return await self.post_organizations(payload)

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_organizations(**params)
        return await self.get_organizations()

    async def update(self, id: str, payload):
        """Update entity (delegates to generated PATCH method)."""
        return await self.patch_organization_by_id_archive(id, payload)

    async def delete(self, id: str):
        """Delete entity (delegates to generated DELETE method)."""
        return await self.delete_organization_by_id(id)

    async def patch_organization_token(self, organization_id: str, payload: OrganizationUpdateTokenUpdate, type: str) -> Dict[str, Any]:
        """Patch Organizations Token"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/{organization_id}/token", json=json_data)
        if data:
            return Dict[str, Any].model_validate(data)
        return data

    async def post_organizations(self, payload: OrganizationCreate) -> OrganizationGet:
        """Create Organizations"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "", json=json_data)
        if data:
            return OrganizationGet.model_validate(data)
        return data

    async def get_organizations(self, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, title: Optional[str] = None, description: Optional[str] = None, path: Optional[str] = None, organization_type: Optional[str] = None, user_id: Optional[str] = None, number: Optional[str] = None, email: Optional[str] = None, telephone: Optional[str] = None, fax_number: Optional[str] = None, url: Optional[str] = None, postal_code: Optional[str] = None, street_address: Optional[str] = None, locality: Optional[str] = None, region: Optional[str] = None, country: Optional[str] = None) -> List[OrganizationList]:
        """List Organizations"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'id', 'title', 'description', 'path', 'organization_type', 'user_id', 'number', 'email', 'telephone', 'fax_number', 'url', 'postal_code', 'street_address', 'locality', 'region', 'country'] and v is not None}
        data = await self._request("GET", "", params=params)
        if isinstance(data, list):
            return [OrganizationList.model_validate(item) for item in data]
        return data

    async def get_organization_by_id(self, id: str) -> OrganizationGet:
        """Get Organizations"""
        data = await self._request("GET", f"/{id}")
        if data:
            return OrganizationGet.model_validate(data)
        return data

    async def patch_organization_by_id(self, id: str, payload: OrganizationUpdate) -> OrganizationGet:
        """Update Organizations"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/{id}", json=json_data)
        if data:
            return OrganizationGet.model_validate(data)
        return data

    async def delete_organization_by_id(self, id: str) -> Any:
        """Delete Organizations"""
        data = await self._request("DELETE", f"/{id}")

    async def patch_organization_by_id_archive(self, id: str) -> Any:
        """Route Organizations"""
        data = await self._request("PATCH", f"/{id}/archive")
