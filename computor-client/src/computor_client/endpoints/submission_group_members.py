"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.submission_group_members import (
    SubmissionGroupMemberCreate,
    SubmissionGroupMemberGet,
    SubmissionGroupMemberList,
    SubmissionGroupMemberUpdate,
)

from computor_client.http import AsyncHTTPClient


class SubmissionGroupMembersClient:
    """
    Client for submission group members endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def submission_group_members(
        self,
        data: Union[SubmissionGroupMemberCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> SubmissionGroupMemberGet:
        """Create Submission-Group-Members"""
        response = await self._http.post(f"/submission-group-members", json_data=data, params=kwargs)
        return SubmissionGroupMemberGet.model_validate(response.json())

    async def get_submission_group_members(
        self,
        **kwargs: Any,
    ) -> List[SubmissionGroupMemberList]:
        """List Submission-Group-Members"""
        response = await self._http.get(f"/submission-group-members", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [SubmissionGroupMemberList.model_validate(item) for item in data]
        return []

    async def get_submission_group_members_id(
        self,
        id: str,
        **kwargs: Any,
    ) -> SubmissionGroupMemberGet:
        """Get Submission-Group-Members"""
        response = await self._http.get(f"/submission-group-members/{id}", params=kwargs)
        return SubmissionGroupMemberGet.model_validate(response.json())

    async def patch_submission_group_members(
        self,
        id: str,
        data: Union[SubmissionGroupMemberUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> SubmissionGroupMemberGet:
        """Update Submission-Group-Members"""
        response = await self._http.patch(f"/submission-group-members/{id}", json_data=data, params=kwargs)
        return SubmissionGroupMemberGet.model_validate(response.json())

    async def delete_submission_group_members(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Submission-Group-Members"""
        await self._http.delete(f"/submission-group-members/{id}", params=kwargs)
        return

