"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


from computor_client.http import AsyncHTTPClient


class WorkspacesClient:
    """
    Client for workspaces endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def roles_users(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """List all users with their workspace roles"""
        response = await self._http.get(f"/workspaces/roles/users", params=kwargs)
        return response.json()

    async def roles_assign(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Assign a workspace role by email"""
        response = await self._http.post(f"/workspaces/roles/assign", params=kwargs)
        return response.json()

    async def delete_roles_users(
        self,
        user_id: str,
        role_id: str,
        **kwargs: Any,
    ) -> None:
        """Remove a workspace role from a user"""
        await self._http.delete(f"/workspaces/roles/users/{user_id}/{role_id}", params=kwargs)
        return

