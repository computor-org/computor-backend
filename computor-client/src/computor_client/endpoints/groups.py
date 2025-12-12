"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from computor_types.groups import (
    GroupCreate,
    GroupGet,
    GroupList,
    GroupUpdate,
)

from computor_client.http import AsyncHTTPClient


class GroupsClient:
    """
    Client for groups endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def create(
        self,
        data: Union[GroupCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> GroupGet:
        """Create Groups"""
        response = await self._http.post(f"/groups", json_data=data, params=kwargs)
        return GroupGet.model_validate(response.json())

    async def list(
        self,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[GroupList]:
        """List Groups"""
        params = query.model_dump(exclude_none=True) if query else {}
        params.update(kwargs)
        response = await self._http.get(
            f"/groups",
            params=params,
        )
        data = response.json()
        if isinstance(data, list):
            return [GroupList.model_validate(item) for item in data]
        return []

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> GroupGet:
        """Get Groups"""
        response = await self._http.get(f"/groups/{id}", params=kwargs)
        return GroupGet.model_validate(response.json())

    async def update(
        self,
        id: str,
        data: Union[GroupUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> GroupGet:
        """Update Groups"""
        response = await self._http.patch(f"/groups/{id}", json_data=data, params=kwargs)
        return GroupGet.model_validate(response.json())

    async def delete(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Groups"""
        await self._http.delete(f"/groups/{id}", params=kwargs)
        return

