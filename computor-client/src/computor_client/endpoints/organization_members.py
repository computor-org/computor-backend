"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


from computor_client.http import AsyncHTTPClient


class OrganizationMembersClient:
    """
    Client for organization members endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def create(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Create Organization-Members"""
        response = await self._http.post(f"/organization-members", params=kwargs)
        return response.json()

    async def list(
        self,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """List Organization-Members"""
        params = query.model_dump(exclude_none=True) if query else {}
        params.update(kwargs)
        response = await self._http.get(
            f"/organization-members",
            params=params,
        )
        return response.json()

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Organization-Members"""
        response = await self._http.get(f"/organization-members/{id}", params=kwargs)
        return response.json()

    async def update(
        self,
        id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Update Organization-Members"""
        response = await self._http.patch(f"/organization-members/{id}", params=kwargs)
        return response.json()

    async def delete(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Organization-Members"""
        await self._http.delete(f"/organization-members/{id}", params=kwargs)
        return

