"""Auto-generated client for /service-accounts endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.services import (
    ServiceCreate,
    ServiceGet,
    ServiceUpdate,
)

from computor_client.base import BaseEndpointClient


class ServiceAccountsClient(BaseEndpointClient):
    """Client for /service-accounts endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/service-accounts",
        )

    async def create(self, payload):
        """Create a new entity (delegates to generated POST method)."""
        return await self.post_service_accounts(payload)

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_service_accounts(**params)
        return await self.get_service_accounts()

    async def get(self, id: str):
        """Get entity by ID (delegates to generated GET method)."""
        return await self.get_service_account_by_service_id(id)

    async def update(self, id: str, payload):
        """Update entity (delegates to generated PATCH method)."""
        return await self.patch_service_account_by_service_id(id, payload)

    async def delete(self, id: str):
        """Delete entity (delegates to generated DELETE method)."""
        return await self.delete_service_account_by_service_id(id)

    async def post_service_accounts(self, payload: ServiceCreate, user_id: Optional[str] = None) -> ServiceGet:
        """Create Service Endpoint"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "", json=json_data)
        if data:
            return ServiceGet.model_validate(data)
        return data

    async def get_service_accounts(self, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, slug: Optional[str] = None, service_type_id: Optional[str] = None, enabled: Optional[str] = None, user_id: Optional[str] = None) -> List[ServiceGet]:
        """List Services Endpoint"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'id', 'slug', 'service_type_id', 'enabled', 'user_id'] and v is not None}
        data = await self._request("GET", "", params=params)
        if isinstance(data, list):
            return [ServiceGet.model_validate(item) for item in data]
        return data

    async def get_service_account_by_service_id(self, service_id: str, user_id: Optional[str] = None) -> ServiceGet:
        """Get Service Endpoint"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/{service_id}", params=params)
        if data:
            return ServiceGet.model_validate(data)
        return data

    async def patch_service_account_by_service_id(self, service_id: str, payload: ServiceUpdate, user_id: Optional[str] = None) -> ServiceGet:
        """Update Service Endpoint"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/{service_id}", json=json_data)
        if data:
            return ServiceGet.model_validate(data)
        return data

    async def delete_service_account_by_service_id(self, service_id: str, user_id: Optional[str] = None) -> Any:
        """Delete Service Endpoint"""
        data = await self._request("DELETE", f"/{service_id}")

    async def put_service_account_heartbeat(self, service_id: str, user_id: Optional[str] = None) -> Any:
        """Service Heartbeat Endpoint"""
        data = await self._request("PUT", f"/{service_id}/heartbeat")
