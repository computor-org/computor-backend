"""Auto-generated client for /example-repositories endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.example import (
    ExampleRepositoryCreate,
    ExampleRepositoryGet,
    ExampleRepositoryList,
    ExampleRepositoryUpdate,
)

from computor_client.base import BaseEndpointClient


class ExampleRepositoriesClient(BaseEndpointClient):
    """Client for /example-repositories endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/example-repositories",
        )

    async def create(self, payload):
        """Create a new entity (delegates to generated POST method)."""
        return await self.post_example_repositories(payload)

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_example_repositories(**params)
        return await self.get_example_repositories()

    async def update(self, id: str, payload):
        """Update entity (delegates to generated PATCH method)."""
        return await self.patch_example_repository_by_id(id, payload)

    async def delete(self, id: str):
        """Delete entity (delegates to generated DELETE method)."""
        return await self.delete_example_repository_by_id(id)

    async def post_example_repositories(self, payload: ExampleRepositoryCreate) -> ExampleRepositoryGet:
        """Create Example-Repositories"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "", json=json_data)
        if data:
            return ExampleRepositoryGet.model_validate(data)
        return data

    async def get_example_repositories(self, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, name: Optional[str] = None, source_type: Optional[str] = None, organization_id: Optional[str] = None) -> List[ExampleRepositoryList]:
        """List Example-Repositories"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'id', 'name', 'source_type', 'organization_id'] and v is not None}
        data = await self._request("GET", "", params=params)
        if isinstance(data, list):
            return [ExampleRepositoryList.model_validate(item) for item in data]
        return data

    async def get_example_repository_by_id(self, id: str) -> ExampleRepositoryGet:
        """Get Example-Repositories"""
        data = await self._request("GET", f"/{id}")
        if data:
            return ExampleRepositoryGet.model_validate(data)
        return data

    async def patch_example_repository_by_id(self, id: str, payload: ExampleRepositoryUpdate) -> ExampleRepositoryGet:
        """Update Example-Repositories"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/{id}", json=json_data)
        if data:
            return ExampleRepositoryGet.model_validate(data)
        return data

    async def delete_example_repository_by_id(self, id: str) -> Any:
        """Delete Example-Repositories"""
        data = await self._request("DELETE", f"/{id}")
