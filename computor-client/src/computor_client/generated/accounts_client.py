"""Auto-generated client for /accounts endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.accounts import (
    AccountCreate,
    AccountGet,
    AccountList,
    AccountUpdate,
)

from computor_client.base import BaseEndpointClient


class AccountsClient(BaseEndpointClient):
    """Client for /accounts endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/accounts",
        )

    async def create(self, payload):
        """Create a new entity (delegates to generated POST method)."""
        return await self.post_accounts(payload)

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_accounts(**params)
        return await self.get_accounts()

    async def get(self, id: str):
        """Get entity by ID (delegates to generated GET method)."""
        return await self.get_account_by_id(id)

    async def update(self, id: str, payload):
        """Update entity (delegates to generated PATCH method)."""
        return await self.patch_account_by_id(id, payload)

    async def delete(self, id: str):
        """Delete entity (delegates to generated DELETE method)."""
        return await self.delete_account_by_id(id)

    async def post_accounts(self, payload: AccountCreate, user_id: Optional[str] = None) -> AccountGet:
        """Create Accounts"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "", json=json_data)
        if data:
            return AccountGet.model_validate(data)
        return data

    async def get_accounts(self, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, provider: Optional[str] = None, type: Optional[str] = None, provider_account_id: Optional[str] = None, user_id: Optional[str] = None) -> List[AccountList]:
        """List Accounts"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'id', 'provider', 'type', 'provider_account_id', 'user_id'] and v is not None}
        data = await self._request("GET", "", params=params)
        if isinstance(data, list):
            return [AccountList.model_validate(item) for item in data]
        return data

    async def get_account_by_id(self, id: str, user_id: Optional[str] = None) -> AccountGet:
        """Get Accounts"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/{id}", params=params)
        if data:
            return AccountGet.model_validate(data)
        return data

    async def patch_account_by_id(self, id: str, payload: AccountUpdate, user_id: Optional[str] = None) -> AccountGet:
        """Update Accounts"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/{id}", json=json_data)
        if data:
            return AccountGet.model_validate(data)
        return data

    async def delete_account_by_id(self, id: str, user_id: Optional[str] = None) -> Any:
        """Delete Accounts"""
        data = await self._request("DELETE", f"/{id}")
