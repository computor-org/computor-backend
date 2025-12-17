"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from computor_types.users import (
    UserCreate,
    UserGet,
    UserList,
    UserUpdate,
)

from computor_client.http import AsyncHTTPClient


class UsersClient:
    """
    Client for users endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def create(
        self,
        data: Union[UserCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> UserGet:
        """Create Users"""
        response = await self._http.post(f"/users", json_data=data, params=kwargs)
        return UserGet.model_validate(response.json())

    async def list(
        self,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[UserList]:
        """List Users"""
        params = query.model_dump(exclude_none=True) if query else {}
        params.update(kwargs)
        response = await self._http.get(
            f"/users",
            params=params,
        )
        data = response.json()
        if isinstance(data, list):
            return [UserList.model_validate(item) for item in data]
        return []

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> UserGet:
        """Get Users"""
        response = await self._http.get(f"/users/{id}", params=kwargs)
        return UserGet.model_validate(response.json())

    async def update(
        self,
        id: str,
        data: Union[UserUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> UserGet:
        """Update Users"""
        response = await self._http.patch(f"/users/{id}", json_data=data, params=kwargs)
        return UserGet.model_validate(response.json())

    async def delete(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Users"""
        await self._http.delete(f"/users/{id}", params=kwargs)
        return

    async def archive(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Route Users"""
        response = await self._http.patch(f"/users/{id}/archive", params=kwargs)
        return

