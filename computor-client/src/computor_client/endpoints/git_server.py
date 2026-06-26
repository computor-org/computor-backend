"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


from computor_client.http import AsyncHTTPClient


class GitServerClient:
    """
    Client for git server endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def health(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Git Health"""
        response = await self._http.get(f"/git/health", params=kwargs)
        return response.json()

    async def users(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Create Git User"""
        response = await self._http.post(f"/git/users", params=kwargs)
        return response.json()

    async def get_users(
        self,
        username: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Git User"""
        response = await self._http.get(f"/git/users/{username}", params=kwargs)
        return response.json()

    async def patch_users(
        self,
        username: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Update Git User"""
        response = await self._http.patch(f"/git/users/{username}", params=kwargs)
        return response.json()

    async def delete_users(
        self,
        username: str,
        **kwargs: Any,
    ) -> None:
        """Delete Git User"""
        await self._http.delete(f"/git/users/{username}", params=kwargs)
        return

    async def users_suspend(
        self,
        username: str,
        **kwargs: Any,
    ) -> None:
        """Suspend Git User"""
        response = await self._http.post(f"/git/users/{username}/suspend", params=kwargs)
        return

    async def users_activate(
        self,
        username: str,
        **kwargs: Any,
    ) -> None:
        """Activate Git User"""
        response = await self._http.post(f"/git/users/{username}/activate", params=kwargs)
        return

