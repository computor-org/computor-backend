"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from computor_types.accounts import (
    AccountCreate,
    AccountGet,
    AccountList,
    AccountProvider,
    AccountUpdate,
)

from computor_client.http import AsyncHTTPClient
from computor_client.pagination import Page
from computor_client.urls import quote_path


class AccountsClient:
    """
    Client for accounts endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[AccountList]:
        """List Accounts"""
        page = await self.list_page(skip=skip, limit=limit, query=query, **kwargs)
        return page.items

    async def list_page(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> Page[AccountList]:
        """List Accounts (one page, with the total row count)."""
        params = query.model_dump(mode="json", exclude_none=True) if query else {}
        params.update({"skip": skip, "limit": limit})
        params.update(kwargs)
        response = await self._http.get(f"/accounts", params=params)
        return Page.from_response(response, AccountList, skip=skip, limit=limit)

    async def create(
        self,
        data: Union[AccountCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> AccountGet:
        """Create Accounts"""
        response = await self._http.post(f"/accounts", json_data=data, params=kwargs)
        return AccountGet.model_validate(response.json())

    async def list_providers(
        self,
        **kwargs: Any,
    ) -> List[AccountProvider]:
        """List Account Providers"""
        response = await self._http.get(f"/accounts/providers", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [AccountProvider.model_validate(item) for item in data]
        return []

    async def delete(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Accounts"""
        await self._http.delete(f"/accounts/{quote_path(id)}", params=kwargs)
        return

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> AccountGet:
        """Get Accounts"""
        response = await self._http.get(f"/accounts/{quote_path(id)}", params=kwargs)
        return AccountGet.model_validate(response.json())

    async def update(
        self,
        id: str,
        data: Union[AccountUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> AccountGet:
        """Update Accounts"""
        response = await self._http.patch(f"/accounts/{quote_path(id)}", json_data=data, params=kwargs)
        return AccountGet.model_validate(response.json())

