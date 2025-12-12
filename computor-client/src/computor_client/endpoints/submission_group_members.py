"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

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

    async def create(
        self,
        data: Union[SubmissionGroupMemberCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> SubmissionGroupMemberGet:
        """Create Submission-Group-Members"""
        response = await self._http.post(f"/submission-group-members", json_data=data, params=kwargs)
        return SubmissionGroupMemberGet.model_validate(response.json())

    async def list(
        self,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[SubmissionGroupMemberList]:
        """List Submission-Group-Members"""
        params = query.model_dump(exclude_none=True) if query else {}
        params.update(kwargs)
        response = await self._http.get(
            f"/submission-group-members",
            params=params,
        )
        data = response.json()
        if isinstance(data, list):
            return [SubmissionGroupMemberList.model_validate(item) for item in data]
        return []

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> SubmissionGroupMemberGet:
        """Get Submission-Group-Members"""
        response = await self._http.get(f"/submission-group-members/{id}", params=kwargs)
        return SubmissionGroupMemberGet.model_validate(response.json())

    async def update(
        self,
        id: str,
        data: Union[SubmissionGroupMemberUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> SubmissionGroupMemberGet:
        """Update Submission-Group-Members"""
        response = await self._http.patch(f"/submission-group-members/{id}", json_data=data, params=kwargs)
        return SubmissionGroupMemberGet.model_validate(response.json())

    async def delete(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Submission-Group-Members"""
        await self._http.delete(f"/submission-group-members/{id}", params=kwargs)
        return

