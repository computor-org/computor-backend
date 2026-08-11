"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from computor_types.course_content_types import (
    CourseContentTypeCreate,
    CourseContentTypeGet,
    CourseContentTypeList,
    CourseContentTypeUpdate,
)

from computor_client.http import AsyncHTTPClient
from computor_client.pagination import Page
from computor_client.urls import quote_path


class CourseContentTypesClient:
    """
    Client for course content types endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[CourseContentTypeList]:
        """List Course-Content-Types"""
        page = await self.list_page(skip=skip, limit=limit, query=query, **kwargs)
        return page.items

    async def list_page(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> Page[CourseContentTypeList]:
        """List Course-Content-Types (one page, with the total row count)."""
        params = query.model_dump(mode="json", exclude_none=True) if query else {}
        params.update({"skip": skip, "limit": limit})
        params.update(kwargs)
        response = await self._http.get(f"/course-content-types", params=params)
        return Page.from_response(response, CourseContentTypeList, skip=skip, limit=limit)

    async def create(
        self,
        data: Union[CourseContentTypeCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseContentTypeGet:
        """Create Course-Content-Types"""
        response = await self._http.post(f"/course-content-types", json_data=data, params=kwargs)
        return CourseContentTypeGet.model_validate(response.json())

    async def delete(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Course-Content-Types"""
        await self._http.delete(f"/course-content-types/{quote_path(id)}", params=kwargs)
        return

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> CourseContentTypeGet:
        """Get Course-Content-Types"""
        response = await self._http.get(f"/course-content-types/{quote_path(id)}", params=kwargs)
        return CourseContentTypeGet.model_validate(response.json())

    async def update(
        self,
        id: str,
        data: Union[CourseContentTypeUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseContentTypeGet:
        """Update Course-Content-Types"""
        response = await self._http.patch(f"/course-content-types/{quote_path(id)}", json_data=data, params=kwargs)
        return CourseContentTypeGet.model_validate(response.json())

