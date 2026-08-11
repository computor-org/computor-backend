"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Union

from computor_types.invites import (
    InviteAccept,
    InviteLinkCreate,
    InviteLinkGet,
    InviteLinkList,
    InviteLinkPublic,
)

from computor_client.http import AsyncHTTPClient
from computor_client.urls import quote_path


class InvitesClient:
    """
    Client for invites endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list_admin(
        self,
        **kwargs: Any,
    ) -> List[InviteLinkList]:
        """List Invites"""
        response = await self._http.get("/admin/invites", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [InviteLinkList.model_validate(item) for item in data]
        return []

    async def admin(
        self,
        data: Union[InviteLinkCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> InviteLinkGet:
        """Create Invite"""
        response = await self._http.post("/admin/invites", json_data=data, params=kwargs)
        return InviteLinkGet.model_validate(response.json())

    async def delete_admin(
        self,
        invite_id: str,
        **kwargs: Any,
    ) -> None:
        """Revoke Invite"""
        await self._http.delete(f"/admin/invites/{quote_path(invite_id)}", params=kwargs)
        return

    async def get_admin(
        self,
        invite_id: str,
        **kwargs: Any,
    ) -> InviteLinkGet:
        """Get Invite"""
        response = await self._http.get(f"/admin/invites/{quote_path(invite_id)}", params=kwargs)
        return InviteLinkGet.model_validate(response.json())

    async def get(
        self,
        token: str,
        **kwargs: Any,
    ) -> InviteLinkPublic:
        """Get Invite Public"""
        response = await self._http.get(f"/invites/{quote_path(token)}", params=kwargs)
        return InviteLinkPublic.model_validate(response.json())

    async def accept(
        self,
        token: str,
        data: Union[InviteAccept, Dict[str, Any]],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Accept Invite"""
        response = await self._http.post(f"/invites/{quote_path(token)}/accept", json_data=data, params=kwargs)
        return response.json()

