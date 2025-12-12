"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from computor_types.accounts import (
    AccountCreate,
    AccountGet,
    AccountList,
    AccountUpdate,
)

from computor_client.http import AsyncHTTPClient


class AccountsClient:
    """
    Client for accounts endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def create(
        self,
        data: Union[AccountCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> AccountGet:
        """Create Accounts"""
        response = await self._http.post(f"/accounts", json_data=data, params=kwargs)
        return AccountGet.model_validate(response.json())

    async def list(
        self,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[AccountList]:
        """List Accounts"""
        params = query.model_dump(exclude_none=True) if query else {}
        params.update(kwargs)
        response = await self._http.get(
            f"/accounts",
            params=params,
        )
        data = response.json()
        if isinstance(data, list):
            return [AccountList.model_validate(item) for item in data]
        return []

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> AccountGet:
        """Get Accounts"""
        response = await self._http.get(f"/accounts/{id}", params=kwargs)
        return AccountGet.model_validate(response.json())

    async def update(
        self,
        id: str,
        data: Union[AccountUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> AccountGet:
        """Update Accounts"""
        response = await self._http.patch(f"/accounts/{id}", json_data=data, params=kwargs)
        return AccountGet.model_validate(response.json())

    async def delete(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Accounts"""
        await self._http.delete(f"/accounts/{id}", params=kwargs)
        return

