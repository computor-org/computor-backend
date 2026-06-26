"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


from computor_client.http import AsyncHTTPClient


class InvitesClient:
    """
    Client for invites endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def admin(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Create Invite"""
        response = await self._http.post(f"/admin/invites", params=kwargs)
        return response.json()

    async def get_admin(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """List Invites"""
        response = await self._http.get(f"/admin/invites", params=kwargs)
        return response.json()

    async def get_admin_invites_invite_id(
        self,
        invite_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Invite"""
        response = await self._http.get(f"/admin/invites/{invite_id}", params=kwargs)
        return response.json()

    async def delete_admin(
        self,
        invite_id: str,
        **kwargs: Any,
    ) -> None:
        """Revoke Invite"""
        await self._http.delete(f"/admin/invites/{invite_id}", params=kwargs)
        return

    async def get(
        self,
        token: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Invite Public"""
        response = await self._http.get(f"/invites/{token}", params=kwargs)
        return response.json()

    async def accept(
        self,
        token: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Accept Invite"""
        response = await self._http.post(f"/invites/{token}/accept", params=kwargs)
        return response.json()

