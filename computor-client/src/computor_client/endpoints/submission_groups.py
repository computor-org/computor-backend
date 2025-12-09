"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.submission_groups import (
    SubmissionGroupCreate,
    SubmissionGroupGet,
    SubmissionGroupList,
    SubmissionGroupProperties,
    SubmissionGroupUpdate,
)

from computor_client.http import AsyncHTTPClient


class SubmissionGroupsClient:
    """
    Client for submission groups endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def submission_groups(
        self,
        data: Union[SubmissionGroupCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> SubmissionGroupGet:
        """Create Submission-Groups"""
        response = await self._http.post(f"/submission-groups", json_data=data, params=kwargs)
        return SubmissionGroupGet.model_validate(response.json())

    async def get_submission_groups(
        self,
        **kwargs: Any,
    ) -> List[SubmissionGroupList]:
        """List Submission-Groups"""
        response = await self._http.get(f"/submission-groups", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [SubmissionGroupList.model_validate(item) for item in data]
        return []

    async def get_submission_groups_id(
        self,
        id: str,
        **kwargs: Any,
    ) -> SubmissionGroupGet:
        """Get Submission-Groups"""
        response = await self._http.get(f"/submission-groups/{id}", params=kwargs)
        return SubmissionGroupGet.model_validate(response.json())

    async def patch_submission_groups(
        self,
        id: str,
        data: Union[SubmissionGroupUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> SubmissionGroupGet:
        """Update Submission-Groups"""
        response = await self._http.patch(f"/submission-groups/{id}", json_data=data, params=kwargs)
        return SubmissionGroupGet.model_validate(response.json())

    async def delete_submission_groups(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Submission-Groups"""
        await self._http.delete(f"/submission-groups/{id}", params=kwargs)
        return

