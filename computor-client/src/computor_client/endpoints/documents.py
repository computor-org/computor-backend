"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


from computor_client.http import AsyncHTTPClient


class DocumentsClient:
    """
    Client for documents endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def files(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Upload Document File"""
        response = await self._http.post(f"/documents/files", params=kwargs)
        return response.json()

    async def delete_files(
        self,
        **kwargs: Any,
    ) -> None:
        """Delete Document File"""
        await self._http.delete(f"/documents/files", params=kwargs)
        return

    async def patch_files(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Rename Document File"""
        response = await self._http.patch(f"/documents/files", params=kwargs)
        return response.json()

    async def get_files(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Document File"""
        response = await self._http.get(f"/documents/files", params=kwargs)
        return response.json()

    async def directories(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Create Document Directory"""
        response = await self._http.post(f"/documents/directories", params=kwargs)
        return response.json()

    async def delete_directories(
        self,
        **kwargs: Any,
    ) -> None:
        """Delete Document Directory"""
        await self._http.delete(f"/documents/directories", params=kwargs)
        return

    async def patch_directories(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Rename Document Directory"""
        response = await self._http.patch(f"/documents/directories", params=kwargs)
        return response.json()

    async def list(
        self,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """List Documents Directory"""
        params = query.model_dump(exclude_none=True) if query else {}
        params.update(kwargs)
        response = await self._http.get(
            f"/documents/list",
            params=params,
        )
        return response.json()

