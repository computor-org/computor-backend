"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, List, Optional

from computor_types.course_member_gradings import (
    CourseMemberGradingsGet,
    CourseMemberGradingsList,
)
from pydantic import BaseModel

from computor_client.http import AsyncHTTPClient
from computor_client.pagination import Page
from computor_client.urls import quote_path


class CourseMemberGradingsClient:
    """
    Client for course member gradings endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[CourseMemberGradingsList]:
        """List course member grading statistics for a course"""
        page = await self.list_page(skip=skip, limit=limit, query=query, **kwargs)
        return page.items

    async def list_page(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> Page[CourseMemberGradingsList]:
        """List course member grading statistics for a course (one page, with the total row count)."""
        params = query.model_dump(mode="json", exclude_none=True) if query else {}
        params.update({"skip": skip, "limit": limit})
        params.update(kwargs)
        response = await self._http.get("/course-member-gradings", params=params)
        return Page.from_response(response, CourseMemberGradingsList, skip=skip, limit=limit)

    async def get(
        self,
        course_member_id: str,
        **kwargs: Any,
    ) -> CourseMemberGradingsGet:
        """Get course member grading statistics"""
        response = await self._http.get(f"/course-member-gradings/{quote_path(course_member_id)}", params=kwargs)
        return CourseMemberGradingsGet.model_validate(response.json())

