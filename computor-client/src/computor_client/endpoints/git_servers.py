"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


from computor_client.http import AsyncHTTPClient


class GitServersClient:
    """
    Client for git servers endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def create(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Create Git Server Endpoint"""
        response = await self._http.post(f"/git-servers", params=kwargs)
        return response.json()

    async def list(
        self,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """List Git Servers Endpoint"""
        params = query.model_dump(exclude_none=True) if query else {}
        params.update(kwargs)
        response = await self._http.get(
            f"/git-servers",
            params=params,
        )
        return response.json()

    async def get(
        self,
        server_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Git Server Endpoint"""
        response = await self._http.get(f"/git-servers/{server_id}", params=kwargs)
        return response.json()

    async def update(
        self,
        server_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Update Git Server Endpoint"""
        response = await self._http.patch(f"/git-servers/{server_id}", params=kwargs)
        return response.json()

    async def delete(
        self,
        server_id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Git Server Endpoint"""
        await self._http.delete(f"/git-servers/{server_id}", params=kwargs)
        return

