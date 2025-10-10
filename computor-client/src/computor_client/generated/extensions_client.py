"""Auto-generated client for /extensions endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.extensions import (
    ExtensionMetadata,
    ExtensionPublishResponse,
    ExtensionVersionDetail,
    ExtensionVersionListResponse,
    ExtensionVersionYankRequest,
)

from computor_client.base import FileOperationClient


class ExtensionsClient(FileOperationClient):
    """Client for /extensions endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/extensions",
        )

    async def update(self, id: str, payload):
        """Update entity (delegates to generated PATCH method)."""
        return await self.patch_extension_version_by_version(id, payload)

    async def post_extension_version(self, extension_identity: str) -> ExtensionPublishResponse:
        """Publish Extension Version"""
        data = await self._request("POST", f"/{extension_identity}/versions")
        if data:
            return ExtensionPublishResponse.model_validate(data)
        return data

    async def get_extension_version(self, extension_identity: str, include_yanked: Optional[str] = None, limit: Optional[str] = None, cursor: Optional[str] = None) -> ExtensionVersionListResponse:
        """List Extension Versions"""
        params = {k: v for k, v in locals().items() if k in ['include_yanked', 'limit', 'cursor'] and v is not None}
        data = await self._request("GET", f"/{extension_identity}/versions", params=params)
        if data:
            return ExtensionVersionListResponse.model_validate(data)
        return data

    async def get_extension_download(self, extension_identity: str, version: Optional[str] = None) -> Any:
        """Download Extension"""
        params = {k: v for k, v in locals().items() if k in ['version'] and v is not None}
        data = await self._request("GET", f"/{extension_identity}/download", params=params)

    async def get_extensions(self, limit: Optional[str] = None, offset: Optional[str] = None) -> List[Dict[str, Any]]:
        """List Extensions"""
        params = {k: v for k, v in locals().items() if k in ['limit', 'offset'] and v is not None}
        data = await self._request("GET", "/", params=params)
        if isinstance(data, list):
            return [Dict[str, Any].model_validate(item) for item in data]
        return data

    async def get_extension_by_extension_identity(self, extension_identity: str) -> ExtensionMetadata:
        """Get Extension Metadata"""
        data = await self._request("GET", f"/{extension_identity}")
        if data:
            return ExtensionMetadata.model_validate(data)
        return data

    async def patch_extension_version_by_version(self, extension_identity: str, version: str, payload: ExtensionVersionYankRequest) -> ExtensionVersionDetail:
        """Update Extension Version"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/{extension_identity}/versions/{version}", json=json_data)
        if data:
            return ExtensionVersionDetail.model_validate(data)
        return data
