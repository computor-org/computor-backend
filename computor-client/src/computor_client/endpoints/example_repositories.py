"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.example import (
    ExampleRepositoryCreate,
    ExampleRepositoryGet,
    ExampleRepositoryList,
    ExampleRepositoryUpdate,
)
from pydantic import BaseModel

from computor_client.http import AsyncHTTPClient
from computor_client.pagination import Page
from computor_client.urls import quote_path


class ExampleRepositoriesClient:
    """
    Client for example repositories endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[ExampleRepositoryList]:
        """List Example-Repositories"""
        page = await self.list_page(skip=skip, limit=limit, query=query, **kwargs)
        return page.items

    async def list_page(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> Page[ExampleRepositoryList]:
        """List Example-Repositories (one page, with the total row count)."""
        params = query.model_dump(mode="json", exclude_none=True) if query else {}
        params.update({"skip": skip, "limit": limit})
        params.update(kwargs)
        response = await self._http.get("/example-repositories", params=params)
        return Page.from_response(response, ExampleRepositoryList, skip=skip, limit=limit)

    async def create(
        self,
        data: Union[ExampleRepositoryCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> ExampleRepositoryGet:
        """Create Example-Repositories"""
        response = await self._http.post("/example-repositories", json_data=data, params=kwargs)
        return ExampleRepositoryGet.model_validate(response.json())

    async def delete(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Example-Repositories"""
        await self._http.delete(f"/example-repositories/{quote_path(id)}", params=kwargs)
        return

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> ExampleRepositoryGet:
        """Get Example-Repositories"""
        response = await self._http.get(f"/example-repositories/{quote_path(id)}", params=kwargs)
        return ExampleRepositoryGet.model_validate(response.json())

    async def update(
        self,
        id: str,
        data: Union[ExampleRepositoryUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> ExampleRepositoryGet:
        """Update Example-Repositories"""
        response = await self._http.patch(f"/example-repositories/{quote_path(id)}", json_data=data, params=kwargs)
        return ExampleRepositoryGet.model_validate(response.json())

