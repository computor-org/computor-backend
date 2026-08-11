"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from computor_types.service_type import (
    ServiceTypeCreate,
    ServiceTypeGet,
    ServiceTypeList,
    ServiceTypeUpdate,
)

from computor_client.http import AsyncHTTPClient
from computor_client.pagination import Page
from computor_client.urls import quote_path


class ServiceTypesClient:
    """
    Client for service types endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[ServiceTypeList]:
        """List Service Types"""
        page = await self.list_page(skip=skip, limit=limit, query=query, **kwargs)
        return page.items

    async def list_page(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> Page[ServiceTypeList]:
        """List Service Types (one page, with the total row count)."""
        params = query.model_dump(mode="json", exclude_none=True) if query else {}
        params.update({"skip": skip, "limit": limit})
        params.update(kwargs)
        response = await self._http.get(f"/service-types", params=params)
        return Page.from_response(response, ServiceTypeList, skip=skip, limit=limit)

    async def create(
        self,
        data: Union[ServiceTypeCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> ServiceTypeGet:
        """Create Service Type"""
        response = await self._http.post(f"/service-types", json_data=data, params=kwargs)
        return ServiceTypeGet.model_validate(response.json())

    async def get(
        self,
        entity_id: str,
        **kwargs: Any,
    ) -> ServiceTypeGet:
        """Get Service Type"""
        response = await self._http.get(f"/service-types/{quote_path(entity_id)}", params=kwargs)
        return ServiceTypeGet.model_validate(response.json())

    async def update(
        self,
        entity_id: str,
        data: Union[ServiceTypeUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> ServiceTypeGet:
        """Update Service Type"""
        response = await self._http.patch(f"/service-types/{quote_path(entity_id)}", json_data=data, params=kwargs)
        return ServiceTypeGet.model_validate(response.json())

