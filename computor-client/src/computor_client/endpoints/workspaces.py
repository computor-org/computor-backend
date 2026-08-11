"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Union

from computor_types.workspace_roles import (
    WorkspaceRoleAssign,
    WorkspaceRoleUser,
)

from computor_client.http import AsyncHTTPClient
from computor_client.urls import quote_path


class WorkspacesClient:
    """
    Client for workspaces endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def roles_assign(
        self,
        data: Union[WorkspaceRoleAssign, Dict[str, Any]],
        **kwargs: Any,
    ) -> WorkspaceRoleUser:
        """Assign a workspace role by email"""
        response = await self._http.post("/workspaces/roles/assign", json_data=data, params=kwargs)
        return WorkspaceRoleUser.model_validate(response.json())

    async def list_roles_users(
        self,
        **kwargs: Any,
    ) -> List[WorkspaceRoleUser]:
        """List all users with their workspace roles"""
        response = await self._http.get("/workspaces/roles/users", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [WorkspaceRoleUser.model_validate(item) for item in data]
        return []

    async def delete_roles_users(
        self,
        user_id: str,
        role_id: str,
        **kwargs: Any,
    ) -> None:
        """Remove a workspace role from a user"""
        await self._http.delete(f"/workspaces/roles/users/{quote_path(user_id)}/{quote_path(role_id)}", params=kwargs)
        return

