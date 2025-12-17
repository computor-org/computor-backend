"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from computor_types.extensions import (
    ExtensionMetadata,
    ExtensionPublishResponse,
    ExtensionVersionDetail,
    ExtensionVersionListResponse,
    ExtensionVersionYankRequest,
)

from computor_client.http import AsyncHTTPClient


class ExtensionsClient:
    """
    Client for extensions endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def versions(
        self,
        extension_identity: str,
        **kwargs: Any,
    ) -> ExtensionPublishResponse:
        """Publish Extension Version"""
        response = await self._http.post(f"/extensions/{extension_identity}/versions", params=kwargs)
        return ExtensionPublishResponse.model_validate(response.json())

    async def get_versions(
        self,
        extension_identity: str,
        **kwargs: Any,
    ) -> ExtensionVersionListResponse:
        """List Extension Versions"""
        response = await self._http.get(f"/extensions/{extension_identity}/versions", params=kwargs)
        return ExtensionVersionListResponse.model_validate(response.json())

    async def download(
        self,
        extension_identity: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Download Extension"""
        response = await self._http.get(f"/extensions/{extension_identity}/download", params=kwargs)
        return response.json()

    async def list(
        self,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """List Extensions"""
        params = query.model_dump(exclude_none=True) if query else {}
        params.update(kwargs)
        response = await self._http.get(
            f"/extensions/",
            params=params,
        )
        return response.json()

    async def get(
        self,
        extension_identity: str,
        **kwargs: Any,
    ) -> ExtensionMetadata:
        """Get Extension Metadata"""
        response = await self._http.get(f"/extensions/{extension_identity}", params=kwargs)
        return ExtensionMetadata.model_validate(response.json())

    async def patch_versions(
        self,
        extension_identity: str,
        version: str,
        data: Union[ExtensionVersionYankRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> ExtensionVersionDetail:
        """Update Extension Version"""
        response = await self._http.patch(f"/extensions/{extension_identity}/versions/{version}", json_data=data, params=kwargs)
        return ExtensionVersionDetail.model_validate(response.json())

