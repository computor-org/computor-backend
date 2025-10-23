"""Auto-generated client for /submission-group-members endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.submission_group_members import (
    SubmissionGroupMemberCreate,
    SubmissionGroupMemberGet,
    SubmissionGroupMemberList,
    SubmissionGroupMemberUpdate,
)

from computor_client.base import BaseEndpointClient


class SubmissionGroupMembersClient(BaseEndpointClient):
    """Client for /submission-group-members endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/submission-group-members",
        )

    async def create(self, payload):
        """Create a new entity (delegates to generated POST method)."""
        return await self.post_submission_group_members(payload)

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_submission_group_members(**params)
        return await self.get_submission_group_members()

    async def update(self, id: str, payload):
        """Update entity (delegates to generated PATCH method)."""
        return await self.patch_submission_group_member_by_id(id, payload)

    async def delete(self, id: str):
        """Delete entity (delegates to generated DELETE method)."""
        return await self.delete_submission_group_member_by_id(id)

    async def post_submission_group_members(self, payload: SubmissionGroupMemberCreate) -> SubmissionGroupMemberGet:
        """Create Submission-Group-Members"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "", json=json_data)
        if data:
            return SubmissionGroupMemberGet.model_validate(data)
        return data

    async def get_submission_group_members(self, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, course_id: Optional[str] = None, course_content_id: Optional[str] = None, course_member_id: Optional[str] = None, submission_group_id: Optional[str] = None, grading: Optional[str] = None, status: Optional[str] = None) -> List[SubmissionGroupMemberList]:
        """List Submission-Group-Members"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'id', 'course_id', 'course_content_id', 'course_member_id', 'submission_group_id', 'grading', 'status'] and v is not None}
        data = await self._request("GET", "", params=params)
        if isinstance(data, list):
            return [SubmissionGroupMemberList.model_validate(item) for item in data]
        return data

    async def get_submission_group_member_by_id(self, id: str) -> SubmissionGroupMemberGet:
        """Get Submission-Group-Members"""
        data = await self._request("GET", f"/{id}")
        if data:
            return SubmissionGroupMemberGet.model_validate(data)
        return data

    async def patch_submission_group_member_by_id(self, id: str, payload: SubmissionGroupMemberUpdate) -> SubmissionGroupMemberGet:
        """Update Submission-Group-Members"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/{id}", json=json_data)
        if data:
            return SubmissionGroupMemberGet.model_validate(data)
        return data

    async def delete_submission_group_member_by_id(self, id: str) -> Any:
        """Delete Submission-Group-Members"""
        data = await self._request("DELETE", f"/{id}")
