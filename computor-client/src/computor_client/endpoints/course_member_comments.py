"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from computor_types.course_member_comments import (
    CommentCreate,
    CommentUpdate,
    CourseMemberCommentList,
)

from computor_client.http import AsyncHTTPClient
from computor_client.pagination import Page
from computor_client.urls import quote_path


class CourseMemberCommentsClient:
    """
    Client for course member comments endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[CourseMemberCommentList]:
        """List Comments"""
        page = await self.list_page(skip=skip, limit=limit, query=query, **kwargs)
        return page.items

    async def list_page(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> Page[CourseMemberCommentList]:
        """List Comments (one page, with the total row count)."""
        params = query.model_dump(mode="json", exclude_none=True) if query else {}
        params.update({"skip": skip, "limit": limit})
        params.update(kwargs)
        response = await self._http.get(f"/course-member-comments", params=params)
        return Page.from_response(response, CourseMemberCommentList, skip=skip, limit=limit)

    async def create(
        self,
        data: Union[CommentCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> List[CourseMemberCommentList]:
        """Create Comment"""
        response = await self._http.post(f"/course-member-comments", json_data=data, params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [CourseMemberCommentList.model_validate(item) for item in data]
        return []

    async def delete(
        self,
        course_member_comment_id: str,
        **kwargs: Any,
    ) -> List[CourseMemberCommentList]:
        """Delete Comment"""
        response = await self._http.delete(f"/course-member-comments/{quote_path(course_member_comment_id)}", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [CourseMemberCommentList.model_validate(item) for item in data]
        return []

    async def update(
        self,
        course_member_comment_id: str,
        data: Union[CommentUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> List[CourseMemberCommentList]:
        """Update Comment"""
        response = await self._http.patch(f"/course-member-comments/{quote_path(course_member_comment_id)}", json_data=data, params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [CourseMemberCommentList.model_validate(item) for item in data]
        return []

