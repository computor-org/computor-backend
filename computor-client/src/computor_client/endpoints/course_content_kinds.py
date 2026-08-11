"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.course_content_kind import (
    CourseContentKindCreate,
    CourseContentKindGet,
    CourseContentKindList,
    CourseContentKindUpdate,
)
from pydantic import BaseModel

from computor_client.http import AsyncHTTPClient
from computor_client.pagination import Page
from computor_client.urls import quote_path


class CourseContentKindsClient:
    """
    Client for course content kinds endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[CourseContentKindList]:
        """List Course-Content-Kinds"""
        page = await self.list_page(skip=skip, limit=limit, query=query, **kwargs)
        return page.items

    async def list_page(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> Page[CourseContentKindList]:
        """List Course-Content-Kinds (one page, with the total row count)."""
        params = query.model_dump(mode="json", exclude_none=True) if query else {}
        params.update({"skip": skip, "limit": limit})
        params.update(kwargs)
        response = await self._http.get("/course-content-kinds", params=params)
        return Page.from_response(response, CourseContentKindList, skip=skip, limit=limit)

    async def create(
        self,
        data: Union[CourseContentKindCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseContentKindGet:
        """Create Course-Content-Kinds"""
        response = await self._http.post("/course-content-kinds", json_data=data, params=kwargs)
        return CourseContentKindGet.model_validate(response.json())

    async def delete(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Course-Content-Kinds"""
        await self._http.delete(f"/course-content-kinds/{quote_path(id)}", params=kwargs)
        return

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> CourseContentKindGet:
        """Get Course-Content-Kinds"""
        response = await self._http.get(f"/course-content-kinds/{quote_path(id)}", params=kwargs)
        return CourseContentKindGet.model_validate(response.json())

    async def update(
        self,
        id: str,
        data: Union[CourseContentKindUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseContentKindGet:
        """Update Course-Content-Kinds"""
        response = await self._http.patch(f"/course-content-kinds/{quote_path(id)}", json_data=data, params=kwargs)
        return CourseContentKindGet.model_validate(response.json())

