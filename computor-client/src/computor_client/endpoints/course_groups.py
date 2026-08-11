"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.course_groups import (
    CourseGroupCreate,
    CourseGroupGet,
    CourseGroupList,
    CourseGroupUpdate,
)
from pydantic import BaseModel

from computor_client.http import AsyncHTTPClient
from computor_client.pagination import Page
from computor_client.urls import quote_path


class CourseGroupsClient:
    """
    Client for course groups endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[CourseGroupList]:
        """List Course-Groups"""
        page = await self.list_page(skip=skip, limit=limit, query=query, **kwargs)
        return page.items

    async def list_page(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> Page[CourseGroupList]:
        """List Course-Groups (one page, with the total row count)."""
        params = query.model_dump(mode="json", exclude_none=True) if query else {}
        params.update({"skip": skip, "limit": limit})
        params.update(kwargs)
        response = await self._http.get("/course-groups", params=params)
        return Page.from_response(response, CourseGroupList, skip=skip, limit=limit)

    async def create(
        self,
        data: Union[CourseGroupCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseGroupGet:
        """Create Course-Groups"""
        response = await self._http.post("/course-groups", json_data=data, params=kwargs)
        return CourseGroupGet.model_validate(response.json())

    async def delete(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Course-Groups"""
        await self._http.delete(f"/course-groups/{quote_path(id)}", params=kwargs)
        return

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> CourseGroupGet:
        """Get Course-Groups"""
        response = await self._http.get(f"/course-groups/{quote_path(id)}", params=kwargs)
        return CourseGroupGet.model_validate(response.json())

    async def update(
        self,
        id: str,
        data: Union[CourseGroupUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseGroupGet:
        """Update Course-Groups"""
        response = await self._http.patch(f"/course-groups/{quote_path(id)}", json_data=data, params=kwargs)
        return CourseGroupGet.model_validate(response.json())

