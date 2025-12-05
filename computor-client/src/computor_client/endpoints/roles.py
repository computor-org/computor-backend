"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.roles import (
    RoleGet,
    RoleList,
)
from computor_types.roles_claims import RoleClaimList

from computor_client.http import AsyncHTTPClient


class RolesClient:
    """
    Client for roles endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> RoleGet:
        """Get Roles"""
        response = await self._http.get(f"/roles/{id}", params=kwargs)
        return RoleGet.model_validate(response.json())

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        **kwargs: Any,
    ) -> List[RoleList]:
        """List Roles"""
        response = await self._http.get(
            f"/roles",
            params={"skip": skip, "limit": limit, **kwargs},
        )
        data = response.json()
        if isinstance(data, list):
            return [RoleList.model_validate(item) for item in data]
        return []

    async def role_claims(
        self,
        **kwargs: Any,
    ) -> List[RoleClaimList]:
        """List Role Claim"""
        response = await self._http.get(f"/role-claims", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [RoleClaimList.model_validate(item) for item in data]
        return []

