"""Auto-generated client for /api-tokens endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.api_tokens import (
    ApiTokenAdminCreate,
    ApiTokenCreate,
    ApiTokenCreateResponse,
    ApiTokenGet,
    ApiTokenUpdate,
)

from computor_client.base import BaseEndpointClient


class ApiTokensClient(BaseEndpointClient):
    """Client for /api-tokens endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/api-tokens",
        )

    async def create(self, payload):
        """Create a new entity (delegates to generated POST method)."""
        return await self.post_api_tokens(payload)

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_api_tokens(**params)
        return await self.get_api_tokens()

    async def get(self, id: str):
        """Get entity by ID (delegates to generated GET method)."""
        return await self.get_api_token_by_token_id(id)

    async def delete(self, id: str):
        """Delete entity (delegates to generated DELETE method)."""
        return await self.delete_api_token_by_token_id(id)

    async def post_api_tokens(self, payload: ApiTokenCreate, user_id: Optional[str] = None) -> ApiTokenCreateResponse:
        """Create Token Endpoint"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "", json=json_data)
        if data:
            return ApiTokenCreateResponse.model_validate(data)
        return data

    async def get_api_tokens(self, user_id: Optional[str] = None, include_revoked: Optional[str] = None) -> List[ApiTokenGet]:
        """List Tokens Endpoint"""
        params = {k: v for k, v in locals().items() if k in ['user_id', 'include_revoked'] and v is not None}
        data = await self._request("GET", "", params=params)
        if isinstance(data, list):
            return [ApiTokenGet.model_validate(item) for item in data]
        return data

    async def post_api_tokens_admin_create(self, payload: ApiTokenAdminCreate, user_id: Optional[str] = None) -> ApiTokenCreateResponse:
        """Create Token Admin Endpoint"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "/admin/create", json=json_data)
        if data:
            return ApiTokenCreateResponse.model_validate(data)
        return data

    async def patch_api_token_admin_by_token_id(self, token_id: str, payload: ApiTokenUpdate, user_id: Optional[str] = None) -> ApiTokenGet:
        """Update Token Admin Endpoint"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/admin/{token_id}", json=json_data)
        if data:
            return ApiTokenGet.model_validate(data)
        return data

    async def get_api_token_by_token_id(self, token_id: str, user_id: Optional[str] = None) -> ApiTokenGet:
        """Get Token Endpoint"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/{token_id}", params=params)
        if data:
            return ApiTokenGet.model_validate(data)
        return data

    async def delete_api_token_by_token_id(self, token_id: str, reason: Optional[str] = None, user_id: Optional[str] = None) -> Any:
        """Revoke Token Endpoint"""
        data = await self._request("DELETE", f"/{token_id}")
