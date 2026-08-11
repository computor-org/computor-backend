"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from computor_types.git_registry import (
    GitServerCreate,
    GitServerGet,
    GitServerUpdate,
)

from computor_client.http import AsyncHTTPClient
from computor_client.pagination import Page
from computor_client.urls import quote_path


class GitServersClient:
    """
    Client for git servers endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[GitServerGet]:
        """List Git Servers Endpoint"""
        page = await self.list_page(skip=skip, limit=limit, query=query, **kwargs)
        return page.items

    async def list_page(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> Page[GitServerGet]:
        """List Git Servers Endpoint (one page, with the total row count)."""
        params = query.model_dump(mode="json", exclude_none=True) if query else {}
        params.update({"skip": skip, "limit": limit})
        params.update(kwargs)
        response = await self._http.get(f"/git-servers", params=params)
        return Page.from_response(response, GitServerGet, skip=skip, limit=limit)

    async def create(
        self,
        data: Union[GitServerCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> GitServerGet:
        """Create Git Server Endpoint"""
        response = await self._http.post(f"/git-servers", json_data=data, params=kwargs)
        return GitServerGet.model_validate(response.json())

    async def delete(
        self,
        server_id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Git Server Endpoint"""
        await self._http.delete(f"/git-servers/{quote_path(server_id)}", params=kwargs)
        return

    async def get(
        self,
        server_id: str,
        **kwargs: Any,
    ) -> GitServerGet:
        """Get Git Server Endpoint"""
        response = await self._http.get(f"/git-servers/{quote_path(server_id)}", params=kwargs)
        return GitServerGet.model_validate(response.json())

    async def update(
        self,
        server_id: str,
        data: Union[GitServerUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> GitServerGet:
        """Update Git Server Endpoint"""
        response = await self._http.patch(f"/git-servers/{quote_path(server_id)}", json_data=data, params=kwargs)
        return GitServerGet.model_validate(response.json())

