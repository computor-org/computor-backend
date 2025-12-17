"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
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


class ServiceTypesClient:
    """
    Client for service types endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def create(
        self,
        data: Union[ServiceTypeCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> ServiceTypeGet:
        """Create Service Type"""
        response = await self._http.post(f"/service-types", json_data=data, params=kwargs)
        return ServiceTypeGet.model_validate(response.json())

    async def list(
        self,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[ServiceTypeList]:
        """List Service Types"""
        params = query.model_dump(exclude_none=True) if query else {}
        params.update(kwargs)
        response = await self._http.get(
            f"/service-types",
            params=params,
        )
        data = response.json()
        if isinstance(data, list):
            return [ServiceTypeList.model_validate(item) for item in data]
        return []

    async def get(
        self,
        entity_id: str,
        **kwargs: Any,
    ) -> ServiceTypeGet:
        """Get Service Type"""
        response = await self._http.get(f"/service-types/{entity_id}", params=kwargs)
        return ServiceTypeGet.model_validate(response.json())

    async def update(
        self,
        entity_id: str,
        data: Union[ServiceTypeUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> ServiceTypeGet:
        """Update Service Type"""
        response = await self._http.patch(f"/service-types/{entity_id}", json_data=data, params=kwargs)
        return ServiceTypeGet.model_validate(response.json())

