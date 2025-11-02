"""Auto-generated client for /service-types endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.service_type import (
    ServiceTypeCreate,
    ServiceTypeGet,
    ServiceTypeList,
    ServiceTypeUpdate,
)

from computor_client.base import BaseEndpointClient


class ServiceTypesClient(BaseEndpointClient):
    """Client for /service-types endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/service-types",
        )

    async def create(self, payload):
        """Create a new entity (delegates to generated POST method)."""
        return await self.post_service_types(payload)

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_service_types(**params)
        return await self.get_service_types()

    async def get(self, id: str):
        """Get entity by ID (delegates to generated GET method)."""
        return await self.get_service_type_by_entity_id(id)

    async def update(self, id: str, payload):
        """Update entity (delegates to generated PATCH method)."""
        return await self.patch_service_type_by_entity_id(id, payload)

    async def post_service_types(self, payload: ServiceTypeCreate, user_id: Optional[str] = None) -> ServiceTypeGet:
        """Create Service Type"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "", json=json_data)
        if data:
            return ServiceTypeGet.model_validate(data)
        return data

    async def get_service_types(self, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, path: Optional[str] = None, path_descendant: Optional[str] = None, path_pattern: Optional[str] = None, category: Optional[str] = None, enabled: Optional[str] = None, plugin_module: Optional[str] = None, user_id: Optional[str] = None) -> List[ServiceTypeList]:
        """List Service Types"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'id', 'path', 'path_descendant', 'path_pattern', 'category', 'enabled', 'plugin_module', 'user_id'] and v is not None}
        data = await self._request("GET", "", params=params)
        if isinstance(data, list):
            return [ServiceTypeList.model_validate(item) for item in data]
        return data

    async def get_service_type_by_entity_id(self, entity_id: str, user_id: Optional[str] = None) -> ServiceTypeGet:
        """Get Service Type"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/{entity_id}", params=params)
        if data:
            return ServiceTypeGet.model_validate(data)
        return data

    async def patch_service_type_by_entity_id(self, entity_id: str, payload: ServiceTypeUpdate, user_id: Optional[str] = None) -> ServiceTypeGet:
        """Update Service Type"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/{entity_id}", json=json_data)
        if data:
            return ServiceTypeGet.model_validate(data)
        return data
