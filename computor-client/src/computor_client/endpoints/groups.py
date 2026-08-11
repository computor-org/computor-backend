"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.groups import (
    GroupCreate,
    GroupGet,
    GroupList,
    GroupUpdate,
)
from pydantic import BaseModel

from computor_client.http import AsyncHTTPClient
from computor_client.pagination import Page
from computor_client.urls import quote_path


class GroupsClient:
    """
    Client for groups endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[GroupList]:
        """List Groups"""
        page = await self.list_page(skip=skip, limit=limit, query=query, **kwargs)
        return page.items

    async def list_page(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> Page[GroupList]:
        """List Groups (one page, with the total row count)."""
        params = query.model_dump(mode="json", exclude_none=True) if query else {}
        params.update({"skip": skip, "limit": limit})
        params.update(kwargs)
        response = await self._http.get("/groups", params=params)
        return Page.from_response(response, GroupList, skip=skip, limit=limit)

    async def create(
        self,
        data: Union[GroupCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> GroupGet:
        """Create Groups"""
        response = await self._http.post("/groups", json_data=data, params=kwargs)
        return GroupGet.model_validate(response.json())

    async def delete(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Groups"""
        await self._http.delete(f"/groups/{quote_path(id)}", params=kwargs)
        return

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> GroupGet:
        """Get Groups"""
        response = await self._http.get(f"/groups/{quote_path(id)}", params=kwargs)
        return GroupGet.model_validate(response.json())

    async def update(
        self,
        id: str,
        data: Union[GroupUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> GroupGet:
        """Update Groups"""
        response = await self._http.patch(f"/groups/{quote_path(id)}", json_data=data, params=kwargs)
        return GroupGet.model_validate(response.json())

