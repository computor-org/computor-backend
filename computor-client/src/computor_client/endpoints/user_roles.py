"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from computor_types.user_roles import (
    UserRoleCreate,
    UserRoleGet,
    UserRoleList,
)

from computor_client.http import AsyncHTTPClient


class UserRolesClient:
    """
    Client for user roles endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list(
        self,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[UserRoleList]:
        """List User Roles"""
        params = query.model_dump(exclude_none=True) if query else {}
        params.update(kwargs)
        response = await self._http.get(
            f"/user-roles",
            params=params,
        )
        data = response.json()
        if isinstance(data, list):
            return [UserRoleList.model_validate(item) for item in data]
        return []

    async def create(
        self,
        data: Union[UserRoleCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> UserRoleGet:
        """Create User Role"""
        response = await self._http.post(f"/user-roles", json_data=data, params=kwargs)
        return UserRoleGet.model_validate(response.json())

    async def get_users(
        self,
        user_id: str,
        role_id: str,
        **kwargs: Any,
    ) -> UserRoleGet:
        """Get User Role Endpoint"""
        response = await self._http.get(f"/user-roles/users/{user_id}/roles/{role_id}", params=kwargs)
        return UserRoleGet.model_validate(response.json())

    async def delete_users(
        self,
        user_id: str,
        role_id: str,
        **kwargs: Any,
    ) -> None:
        """Delete User Role Endpoint"""
        await self._http.delete(f"/user-roles/users/{user_id}/roles/{role_id}", params=kwargs)
        return

