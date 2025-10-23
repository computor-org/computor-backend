"""Auto-generated client for /course-member-comments endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.course_member_comments import (
    CommentCreate,
    CommentUpdate,
    CourseMemberCommentList,
)

from computor_client.base import BaseEndpointClient


class CourseMemberCommentsClient(BaseEndpointClient):
    """Client for /course-member-comments endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/course-member-comments",
        )

    async def create(self, payload):
        """Create a new entity (delegates to generated POST method)."""
        return await self.post_course_member_comments(payload)

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_course_member_comments(**params)
        return await self.get_course_member_comments()

    async def update(self, id: str, payload):
        """Update entity (delegates to generated PATCH method)."""
        return await self.patch_course_member_comment_by_course_member_comment_id(id, payload)

    async def delete(self, id: str):
        """Delete entity (delegates to generated DELETE method)."""
        return await self.delete_course_member_comment_by_course_member_comment_id(id)

    async def get_course_member_comments(self, course_member_id: str) -> List[CourseMemberCommentList]:
        """List Comments"""
        params = {k: v for k, v in locals().items() if k in ['course_member_id'] and v is not None}
        data = await self._request("GET", "", params=params)
        if isinstance(data, list):
            return [CourseMemberCommentList.model_validate(item) for item in data]
        return data

    async def post_course_member_comments(self, payload: CommentCreate) -> List[CourseMemberCommentList]:
        """Create Comment"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "", json=json_data)
        if isinstance(data, list):
            return [CourseMemberCommentList.model_validate(item) for item in data]
        return data

    async def patch_course_member_comment_by_course_member_comment_id(self, course_member_comment_id: str, payload: CommentUpdate) -> List[CourseMemberCommentList]:
        """Update Comment"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/{course_member_comment_id}", json=json_data)
        if isinstance(data, list):
            return [CourseMemberCommentList.model_validate(item) for item in data]
        return data

    async def delete_course_member_comment_by_course_member_comment_id(self, course_member_comment_id: str) -> List[CourseMemberCommentList]:
        """Delete Comment"""
        data = await self._request("DELETE", f"/{course_member_comment_id}")
        if isinstance(data, list):
            return [CourseMemberCommentList.model_validate(item) for item in data]
        return data
