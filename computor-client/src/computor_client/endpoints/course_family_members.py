"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


from computor_client.http import AsyncHTTPClient


class CourseFamilyMembersClient:
    """
    Client for course family members endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def create(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Create Course-Family-Members"""
        response = await self._http.post(f"/course-family-members", params=kwargs)
        return response.json()

    async def list(
        self,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """List Course-Family-Members"""
        params = query.model_dump(exclude_none=True) if query else {}
        params.update(kwargs)
        response = await self._http.get(
            f"/course-family-members",
            params=params,
        )
        return response.json()

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Course-Family-Members"""
        response = await self._http.get(f"/course-family-members/{id}", params=kwargs)
        return response.json()

    async def update(
        self,
        id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Update Course-Family-Members"""
        response = await self._http.patch(f"/course-family-members/{id}", params=kwargs)
        return response.json()

    async def delete(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Course-Family-Members"""
        await self._http.delete(f"/course-family-members/{id}", params=kwargs)
        return

