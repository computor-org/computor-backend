"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from computor_types.cascade_deletion import CascadeDeleteResult
from computor_types.courses import (
    CourseCreate,
    CourseGet,
    CourseList,
    CourseUpdate,
)

from computor_client.http import AsyncHTTPClient
from computor_client.pagination import Page
from computor_client.urls import quote_path


class CoursesClient:
    """
    Client for courses endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[CourseList]:
        """List Courses"""
        page = await self.list_page(skip=skip, limit=limit, query=query, **kwargs)
        return page.items

    async def list_page(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> Page[CourseList]:
        """List Courses (one page, with the total row count)."""
        params = query.model_dump(mode="json", exclude_none=True) if query else {}
        params.update({"skip": skip, "limit": limit})
        params.update(kwargs)
        response = await self._http.get(f"/courses", params=params)
        return Page.from_response(response, CourseList, skip=skip, limit=limit)

    async def create(
        self,
        data: Union[CourseCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseGet:
        """Create Courses"""
        response = await self._http.post(f"/courses", json_data=data, params=kwargs)
        return CourseGet.model_validate(response.json())

    async def delete(
        self,
        course_id: str,
        **kwargs: Any,
    ) -> CascadeDeleteResult:
        """Delete course and all course-specific data"""
        response = await self._http.delete(f"/courses/{quote_path(course_id)}", params=kwargs)
        return CascadeDeleteResult.model_validate(response.json())

    async def get_template(
        self,
        course_id: str,
        **kwargs: Any,
    ) -> bytes:
        """Download the course template as a ZIP"""
        response = await self._http.get(f"/courses/{quote_path(course_id)}/template", params=kwargs)
        return response.content

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> CourseGet:
        """Get Courses"""
        response = await self._http.get(f"/courses/{quote_path(id)}", params=kwargs)
        return CourseGet.model_validate(response.json())

    async def update(
        self,
        id: str,
        data: Union[CourseUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseGet:
        """Update Courses"""
        response = await self._http.patch(f"/courses/{quote_path(id)}", json_data=data, params=kwargs)
        return CourseGet.model_validate(response.json())

