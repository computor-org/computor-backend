"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, List, Optional

from computor_types.roles import (
    RoleGet,
    RoleList,
)
from computor_types.roles_claims import RoleClaimList
from pydantic import BaseModel

from computor_client.http import AsyncHTTPClient
from computor_client.pagination import Page
from computor_client.urls import quote_path


class RolesClient:
    """
    Client for roles endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list_role_claims(
        self,
        **kwargs: Any,
    ) -> List[RoleClaimList]:
        """List Role Claim"""
        response = await self._http.get("/role-claims", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [RoleClaimList.model_validate(item) for item in data]
        return []

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[RoleList]:
        """List Roles"""
        page = await self.list_page(skip=skip, limit=limit, query=query, **kwargs)
        return page.items

    async def list_page(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> Page[RoleList]:
        """List Roles (one page, with the total row count)."""
        params = query.model_dump(mode="json", exclude_none=True) if query else {}
        params.update({"skip": skip, "limit": limit})
        params.update(kwargs)
        response = await self._http.get("/roles", params=params)
        return Page.from_response(response, RoleList, skip=skip, limit=limit)

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> RoleGet:
        """Get Roles"""
        response = await self._http.get(f"/roles/{quote_path(id)}", params=kwargs)
        return RoleGet.model_validate(response.json())

