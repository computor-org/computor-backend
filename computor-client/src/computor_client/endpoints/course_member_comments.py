"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
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


class CourseMemberCommentsClient:
    """
    Client for course member comments endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list(
        self,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[CourseMemberCommentList]:
        """List Comments"""
        params = query.model_dump(exclude_none=True) if query else {}
        params.update(kwargs)
        response = await self._http.get(
            f"/course-member-comments",
            params=params,
        )
        data = response.json()
        if isinstance(data, list):
            return [CourseMemberCommentList.model_validate(item) for item in data]
        return []

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

    async def update(
        self,
        course_member_comment_id: str,
        data: Union[CommentUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> List[CourseMemberCommentList]:
        """Update Comment"""
        response = await self._http.patch(f"/course-member-comments/{course_member_comment_id}", json_data=data, params=kwargs)
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
        await self._http.delete(f"/course-member-comments/{course_member_comment_id}", params=kwargs)
        return

