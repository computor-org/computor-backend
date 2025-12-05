"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.api_tokens import (
    ApiTokenAdminCreate,
    ApiTokenCreate,
    ApiTokenCreateResponse,
    ApiTokenGet,
    ApiTokenUpdate,
)

from computor_client.http import AsyncHTTPClient


class TokensClient:
    """
    Client for tokens endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def api_tokens(
        self,
        data: Union[ApiTokenCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> ApiTokenCreateResponse:
        """Create Token Endpoint"""
        response = await self._http.post(f"/api-tokens", json_data=data, params=kwargs)
        return ApiTokenCreateResponse.model_validate(response.json())

    async def get_api_tokens(
        self,
        **kwargs: Any,
    ) -> List[ApiTokenGet]:
        """List Tokens Endpoint"""
        response = await self._http.get(f"/api-tokens", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [ApiTokenGet.model_validate(item) for item in data]
        return []

    async def api_tokens_admin_create(
        self,
        data: Union[ApiTokenAdminCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> ApiTokenCreateResponse:
        """Create Token Admin Endpoint"""
        response = await self._http.post(f"/api-tokens/admin/create", json_data=data, params=kwargs)
        return ApiTokenCreateResponse.model_validate(response.json())

    async def api_tokens_admin(
        self,
        token_id: str,
        data: Union[ApiTokenUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> ApiTokenGet:
        """Update Token Admin Endpoint"""
        response = await self._http.patch(f"/api-tokens/admin/{token_id}", json_data=data, params=kwargs)
        return ApiTokenGet.model_validate(response.json())

    async def get_api_tokens_token_id(
        self,
        token_id: str,
        **kwargs: Any,
    ) -> ApiTokenGet:
        """Get Token Endpoint"""
        response = await self._http.get(f"/api-tokens/{token_id}", params=kwargs)
        return ApiTokenGet.model_validate(response.json())

    async def delete_api_tokens(
        self,
        token_id: str,
        **kwargs: Any,
    ) -> None:
        """Revoke Token Endpoint"""
        await self._http.delete(f"/api-tokens/{token_id}", params=kwargs)
        return

