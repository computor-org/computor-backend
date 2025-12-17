"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from computor_types.services import (
    ServiceCreate,
    ServiceGet,
    ServiceUpdate,
)

from computor_client.http import AsyncHTTPClient


class ServicesClient:
    """
    Client for services endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def service_accounts(
        self,
        data: Union[ServiceCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> ServiceGet:
        """Create Service Endpoint"""
        response = await self._http.post(f"/service-accounts", json_data=data, params=kwargs)
        return ServiceGet.model_validate(response.json())

    async def get_service_accounts(
        self,
        **kwargs: Any,
    ) -> List[ServiceGet]:
        """List Services Endpoint"""
        response = await self._http.get(f"/service-accounts", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [ServiceGet.model_validate(item) for item in data]
        return []

    async def get_service_accounts_service_id(
        self,
        service_id: str,
        **kwargs: Any,
    ) -> ServiceGet:
        """Get Service Endpoint"""
        response = await self._http.get(f"/service-accounts/{service_id}", params=kwargs)
        return ServiceGet.model_validate(response.json())

    async def patch_service_accounts(
        self,
        service_id: str,
        data: Union[ServiceUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> ServiceGet:
        """Update Service Endpoint"""
        response = await self._http.patch(f"/service-accounts/{service_id}", json_data=data, params=kwargs)
        return ServiceGet.model_validate(response.json())

    async def delete_service_accounts(
        self,
        service_id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Service Endpoint"""
        await self._http.delete(f"/service-accounts/{service_id}", params=kwargs)
        return

    async def service_accounts_heartbeat(
        self,
        service_id: str,
        **kwargs: Any,
    ) -> None:
        """Service Heartbeat Endpoint"""
        response = await self._http.put(f"/service-accounts/{service_id}/heartbeat", params=kwargs)
        return

