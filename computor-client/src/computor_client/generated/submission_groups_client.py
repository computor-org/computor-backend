"""Auto-generated client for /submission-groups endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.submission_groups import (
    SubmissionGroupCreate,
    SubmissionGroupGet,
    SubmissionGroupList,
    SubmissionGroupUpdate,
)
from computor_types.team_management import (
    JoinTeamRequest,
    JoinTeamResponse,
)

from computor_client.base import BaseEndpointClient


class SubmissionGroupsClient(BaseEndpointClient):
    """Client for /submission-groups endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/submission-groups",
        )

    async def create(self, payload):
        """Create a new entity (delegates to generated POST method)."""
        return await self.post_submission_groups(payload)

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_submission_groups(**params)
        return await self.get_submission_groups()

    async def get(self, id: str):
        """Get entity by ID (delegates to generated GET method)."""
        return await self.get_submission_group_by_id(id)

    async def update(self, id: str, payload):
        """Update entity (delegates to generated PATCH method)."""
        return await self.patch_submission_group_by_id(id, payload)

    async def delete(self, id: str):
        """Delete entity (delegates to generated DELETE method)."""
        return await self.delete_submission_group_by_id(id)

    async def post_submission_groups(self, payload: SubmissionGroupCreate, user_id: Optional[str] = None) -> SubmissionGroupGet:
        """Create Submission-Groups"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "", json=json_data)
        if data:
            return SubmissionGroupGet.model_validate(data)
        return data

    async def get_submission_groups(self, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, display_name: Optional[str] = None, max_group_size: Optional[str] = None, max_submissions: Optional[str] = None, course_id: Optional[str] = None, course_content_id: Optional[str] = None, status: Optional[str] = None, user_id: Optional[str] = None) -> List[SubmissionGroupList]:
        """List Submission-Groups"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'id', 'display_name', 'max_group_size', 'max_submissions', 'course_id', 'course_content_id', 'status', 'user_id'] and v is not None}
        data = await self._request("GET", "", params=params)
        if isinstance(data, list):
            return [SubmissionGroupList.model_validate(item) for item in data]
        return data

    async def get_submission_group_by_id(self, id: str, user_id: Optional[str] = None) -> SubmissionGroupGet:
        """Get Submission-Groups"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/{id}", params=params)
        if data:
            return SubmissionGroupGet.model_validate(data)
        return data

    async def patch_submission_group_by_id(self, id: str, payload: SubmissionGroupUpdate, user_id: Optional[str] = None) -> SubmissionGroupGet:
        """Update Submission-Groups"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/{id}", json=json_data)
        if data:
            return SubmissionGroupGet.model_validate(data)
        return data

    async def delete_submission_group_by_id(self, id: str, user_id: Optional[str] = None) -> Any:
        """Delete Submission-Groups"""
        data = await self._request("DELETE", f"/{id}")

    async def post_submission_group_join(self, submission_group_id: str, payload: JoinTeamRequest, user_id: Optional[str] = None) -> JoinTeamResponse:
        """Join Team"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", f"/{submission_group_id}/join", json=json_data)
        if data:
            return JoinTeamResponse.model_validate(data)
        return data
