"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.users import (
    UserBanRequest,
    UserConnectRequest,
    UserConnectResponse,
    UserCreate,
    UserGet,
    UserList,
    UserUpdate,
)
from pydantic import BaseModel

from computor_client.http import AsyncHTTPClient
from computor_client.pagination import Page
from computor_client.urls import quote_path


class UsersClient:
    """
    Client for users endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[UserList]:
        """List Users"""
        page = await self.list_page(skip=skip, limit=limit, query=query, **kwargs)
        return page.items

    async def list_page(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> Page[UserList]:
        """List Users (one page, with the total row count)."""
        params = query.model_dump(mode="json", exclude_none=True) if query else {}
        params.update({"skip": skip, "limit": limit})
        params.update(kwargs)
        response = await self._http.get("/users", params=params)
        return Page.from_response(response, UserList, skip=skip, limit=limit)

    async def create(
        self,
        data: Union[UserCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> UserGet:
        """Create Users"""
        response = await self._http.post("/users", json_data=data, params=kwargs)
        return UserGet.model_validate(response.json())

    async def delete(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Users"""
        await self._http.delete(f"/users/{quote_path(id)}", params=kwargs)
        return

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> UserGet:
        """Get Users"""
        response = await self._http.get(f"/users/{quote_path(id)}", params=kwargs)
        return UserGet.model_validate(response.json())

    async def update(
        self,
        id: str,
        data: Union[UserUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> UserGet:
        """Update Users"""
        response = await self._http.patch(f"/users/{quote_path(id)}", json_data=data, params=kwargs)
        return UserGet.model_validate(response.json())

    async def update_archive(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Route Users"""
        await self._http.patch(f"/users/{quote_path(id)}/archive", params=kwargs)
        return

    async def update_unarchive(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Unarchive Users"""
        await self._http.patch(f"/users/{quote_path(id)}/unarchive", params=kwargs)
        return

    async def update_ban(
        self,
        user_id: str,
        data: Union[UserBanRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> UserGet:
        """Ban User"""
        response = await self._http.patch(f"/users/{quote_path(user_id)}/ban", json_data=data, params=kwargs)
        return UserGet.model_validate(response.json())

    async def connect(
        self,
        user_id: str,
        data: Union[UserConnectRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> UserConnectResponse:
        """Connect User"""
        response = await self._http.post(f"/users/{quote_path(user_id)}/connect", json_data=data, params=kwargs)
        return UserConnectResponse.model_validate(response.json())

    async def update_unban(
        self,
        user_id: str,
        **kwargs: Any,
    ) -> UserGet:
        """Unban User"""
        response = await self._http.patch(f"/users/{quote_path(user_id)}/unban", params=kwargs)
        return UserGet.model_validate(response.json())

