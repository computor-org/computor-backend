"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from computor_types.course_family_members import (
    CourseFamilyMemberCreate,
    CourseFamilyMemberGet,
    CourseFamilyMemberList,
    CourseFamilyMemberUpdate,
)

from computor_client.http import AsyncHTTPClient
from computor_client.pagination import Page
from computor_client.urls import quote_path


class CourseFamilyMembersClient:
    """
    Client for course family members endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[CourseFamilyMemberList]:
        """List Course-Family-Members"""
        page = await self.list_page(skip=skip, limit=limit, query=query, **kwargs)
        return page.items

    async def list_page(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> Page[CourseFamilyMemberList]:
        """List Course-Family-Members (one page, with the total row count)."""
        params = query.model_dump(mode="json", exclude_none=True) if query else {}
        params.update({"skip": skip, "limit": limit})
        params.update(kwargs)
        response = await self._http.get(f"/course-family-members", params=params)
        return Page.from_response(response, CourseFamilyMemberList, skip=skip, limit=limit)

    async def create(
        self,
        data: Union[CourseFamilyMemberCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseFamilyMemberGet:
        """Create Course-Family-Members"""
        response = await self._http.post(f"/course-family-members", json_data=data, params=kwargs)
        return CourseFamilyMemberGet.model_validate(response.json())

    async def delete(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Course-Family-Members"""
        await self._http.delete(f"/course-family-members/{quote_path(id)}", params=kwargs)
        return

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> CourseFamilyMemberGet:
        """Get Course-Family-Members"""
        response = await self._http.get(f"/course-family-members/{quote_path(id)}", params=kwargs)
        return CourseFamilyMemberGet.model_validate(response.json())

    async def update(
        self,
        id: str,
        data: Union[CourseFamilyMemberUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseFamilyMemberGet:
        """Update Course-Family-Members"""
        response = await self._http.patch(f"/course-family-members/{quote_path(id)}", json_data=data, params=kwargs)
        return CourseFamilyMemberGet.model_validate(response.json())

