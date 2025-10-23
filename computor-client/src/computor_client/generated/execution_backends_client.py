"""Auto-generated client for /execution-backends endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.execution_backends import (
    ExecutionBackendCreate,
    ExecutionBackendGet,
    ExecutionBackendList,
    ExecutionBackendUpdate,
)

from computor_client.base import BaseEndpointClient


class ExecutionBackendsClient(BaseEndpointClient):
    """Client for /execution-backends endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/execution-backends",
        )

    async def create(self, payload):
        """Create a new entity (delegates to generated POST method)."""
        return await self.post_execution_backends(payload)

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_execution_backends(**params)
        return await self.get_execution_backends()

    async def update(self, id: str, payload):
        """Update entity (delegates to generated PATCH method)."""
        return await self.patch_execution_backend_by_id(id, payload)

    async def delete(self, id: str):
        """Delete entity (delegates to generated DELETE method)."""
        return await self.delete_execution_backend_by_id(id)

    async def post_execution_backends(self, payload: ExecutionBackendCreate) -> ExecutionBackendGet:
        """Create Execution-Backends"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "", json=json_data)
        if data:
            return ExecutionBackendGet.model_validate(data)
        return data

    async def get_execution_backends(self, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, type: Optional[str] = None, slug: Optional[str] = None) -> List[ExecutionBackendList]:
        """List Execution-Backends"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'id', 'type', 'slug'] and v is not None}
        data = await self._request("GET", "", params=params)
        if isinstance(data, list):
            return [ExecutionBackendList.model_validate(item) for item in data]
        return data

    async def get_execution_backend_by_id(self, id: str) -> ExecutionBackendGet:
        """Get Execution-Backends"""
        data = await self._request("GET", f"/{id}")
        if data:
            return ExecutionBackendGet.model_validate(data)
        return data

    async def patch_execution_backend_by_id(self, id: str, payload: ExecutionBackendUpdate) -> ExecutionBackendGet:
        """Update Execution-Backends"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/{id}", json=json_data)
        if data:
            return ExecutionBackendGet.model_validate(data)
        return data

    async def delete_execution_backend_by_id(self, id: str) -> Any:
        """Delete Execution-Backends"""
        data = await self._request("DELETE", f"/{id}")
